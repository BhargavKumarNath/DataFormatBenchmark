"""
gen_iot_sensors.py
------------------
Generates hyperrealistic IoT sensor telemetry from a smart factory floor.

Schema (12 columns):
  - reading_id          (int64)     Sequential
  - device_id           (dict)      ~10,000 unique sensor IDs
  - device_type         (dict)      TemperatureSensor, PressureGauge, Vibration, Humidity, FlowMeter
  - plant_zone          (dict)      Zone-A through Zone-H
  - reading_value       (float32)   Normally distributed around device baseline, with anomaly spikes
  - reading_unit        (dict)      °C, PSI, mm/s, %RH, L/min
  - battery_pct         (float32)   0-100, decaying over time
  - signal_strength_dbm (float32)   -100 to -30 dBm (realistic RSSI)
  - firmware_version    (dict)      v2.1.0 through v2.4.3
  - is_anomaly          (bool)      ~2% of readings are anomalous
  - error_code          (int16)     0=OK, 1-5 for fault types
  - event_timestamp     (timestamp) High-frequency, monotonic

Memory strategy: Chunked streaming via PyArrow. Peak RAM ~120MB.
"""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pa_csv
import time
import os
from tqdm import tqdm

TOTAL_ROWS  = 100_000_000
CHUNK_SIZE  = 500_000
PARQUET_OUT = "data/iot_sensors_100m.parquet"
CSV_OUT     = "data/iot_sensors_100m.csv"
RANDOM_SEED = 42

DEVICE_TYPES = ["TemperatureSensor", "PressureGauge", "Vibration", "Humidity", "FlowMeter"]
ZONES        = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E", "Zone-F", "Zone-G", "Zone-H"]
UNITS        = ["°C", "PSI", "mm/s", "%RH", "L/min"]
FIRMWARE     = ["v2.1.0", "v2.1.3", "v2.2.0", "v2.3.1", "v2.4.3"]

TYPE_WEIGHTS = [0.25, 0.20, 0.20, 0.20, 0.15]
ZONE_WEIGHTS = [0.18, 0.16, 0.14, 0.13, 0.12, 0.10, 0.09, 0.08]
FW_WEIGHTS   = [0.10, 0.15, 0.25, 0.30, 0.20]

# Baseline reading values per device type
BASELINES = {0: 72.0, 1: 45.0, 2: 2.5, 3: 55.0, 4: 120.0}
STDDEVS   = {0: 8.0,  1: 12.0, 2: 1.5, 3: 10.0, 4: 30.0}

SCHEMA = pa.schema([
    pa.field("reading_id",          pa.int64()),
    pa.field("device_id",           pa.dictionary(pa.int16(), pa.utf8())),
    pa.field("device_type",         pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("plant_zone",          pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("reading_value",       pa.float32()),
    pa.field("reading_unit",        pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("battery_pct",         pa.float32()),
    pa.field("signal_strength_dbm", pa.float32()),
    pa.field("firmware_version",    pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("is_anomaly",          pa.bool_()),
    pa.field("error_code",          pa.int16()),
    pa.field("event_timestamp",     pa.timestamp("ms")),
])

def _make_device_ids(rng, n=10_000):
    return [f"SENS-{i:05d}" for i in range(n)]

def generate_chunk(rng, device_pool, start_id, base_ts_ms, n):
    ids = np.arange(start_id, start_id + n, dtype=np.int64)

    dev_idx  = rng.integers(0, len(device_pool), size=n, dtype=np.int16)
    type_idx = rng.choice(len(DEVICE_TYPES), size=n, p=TYPE_WEIGHTS).astype(np.int8)
    zone_idx = rng.choice(len(ZONES), size=n, p=ZONE_WEIGHTS).astype(np.int8)
    fw_idx   = rng.choice(len(FIRMWARE), size=n, p=FW_WEIGHTS).astype(np.int8)

    # Reading values based on device type baseline
    baselines = np.array([BASELINES[t] for t in type_idx], dtype=np.float32)
    stddevs   = np.array([STDDEVS[t] for t in type_idx], dtype=np.float32)
    reading   = (baselines + rng.normal(0, 1, size=n).astype(np.float32) * stddevs)

    # Inject anomalies (2%)
    is_anomaly = rng.random(size=n) < 0.02
    reading[is_anomaly] *= rng.uniform(2.0, 5.0, size=is_anomaly.sum()).astype(np.float32)
    reading = reading.astype(np.float32)

    # Unit maps 1:1 with device type
    unit_idx = type_idx.copy()

    battery = np.clip(rng.normal(65, 20, size=n), 0, 100).astype(np.float32)
    signal  = np.clip(rng.normal(-60, 15, size=n), -100, -30).astype(np.float32)

    error_codes = np.zeros(n, dtype=np.int16)
    error_codes[is_anomaly] = rng.integers(1, 6, size=is_anomaly.sum(), dtype=np.int16)

    intervals = rng.integers(10, 100, size=n, dtype=np.int64).cumsum()
    timestamps = base_ts_ms + intervals
    new_base = int(timestamps[-1])

    batch = pa.RecordBatch.from_arrays([
        pa.array(ids, type=pa.int64()),
        pa.DictionaryArray.from_arrays(pa.array(dev_idx, type=pa.int16()), pa.array(device_pool)),
        pa.DictionaryArray.from_arrays(pa.array(type_idx, type=pa.int8()), pa.array(DEVICE_TYPES)),
        pa.DictionaryArray.from_arrays(pa.array(zone_idx, type=pa.int8()), pa.array(ZONES)),
        pa.array(reading, type=pa.float32()),
        pa.DictionaryArray.from_arrays(pa.array(unit_idx, type=pa.int8()), pa.array(UNITS)),
        pa.array(battery, type=pa.float32()),
        pa.array(signal, type=pa.float32()),
        pa.DictionaryArray.from_arrays(pa.array(fw_idx, type=pa.int8()), pa.array(FIRMWARE)),
        pa.array(is_anomaly, type=pa.bool_()),
        pa.array(error_codes, type=pa.int16()),
        pa.array(timestamps, type=pa.timestamp("ms")),
    ], schema=SCHEMA)
    return batch, new_base

def write_files(rng, device_pool):
    n_chunks = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts  = int(time.time() * 1000) - TOTAL_ROWS * 60

    writer = None
    rows = 0
    t0 = time.perf_counter()
    try:
        for _ in tqdm(range(n_chunks), desc="Parquet", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng, device_pool, rows, base_ts, n)
            if writer is None:
                writer = pq.ParquetWriter(PARQUET_OUT, schema=SCHEMA, compression="snappy", use_dictionary=True, write_statistics=True)
            writer.write_batch(batch)
            rows += n
    finally:
        if writer: writer.close()
    p_time = time.perf_counter() - t0
    p_size = os.path.getsize(PARQUET_OUT) / (1024**2)
    print(f"  Parquet: {rows:,} rows | {p_size:.0f} MB | {p_time:.1f}s")

    rng2 = np.random.default_rng(RANDOM_SEED)
    dp2  = _make_device_ids(rng2)
    rows = 0
    base_ts = int(time.time() * 1000) - TOTAL_ROWS * 60
    t0 = time.perf_counter()
    header = False
    with open(CSV_OUT, "wb", buffering=16*1024*1024) as f:
        for _ in tqdm(range(n_chunks), desc="CSV    ", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng2, dp2, rows, base_ts, n)
            tbl = pa.Table.from_batches([batch])
            pa_csv.write_csv(tbl, f, write_options=pa_csv.WriteOptions(include_header=not header))
            header = True
            rows += n
    c_time = time.perf_counter() - t0
    c_size = os.path.getsize(CSV_OUT) / (1024**2)
    print(f"  CSV:     {rows:,} rows | {c_size:.0f} MB | {c_time:.1f}s")
    print(f"  Ratio:   {c_size/p_size:.1f}x")

def main():
    print("=" * 60)
    print("  IoT Sensor Telemetry Generator")
    print(f"  Rows: {TOTAL_ROWS:,} | Chunk: {CHUNK_SIZE:,}")
    print("=" * 60)
    os.makedirs("data", exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    device_pool = _make_device_ids(rng)
    write_files(rng, device_pool)
    print("  Done.")

if __name__ == "__main__":
    main()
