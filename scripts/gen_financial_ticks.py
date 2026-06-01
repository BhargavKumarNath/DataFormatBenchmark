"""
gen_financial_ticks.py
----------------------
Generates hyperrealistic stock market tick-level data.

Schema (13 columns):
  - tick_id             (int64)     Sequential
  - symbol              (dict)      ~500 realistic stock tickers
  - exchange            (dict)      NYSE, NASDAQ, LSE, TSE, HKEX
  - tick_type           (dict)      TRADE, BID, ASK, OPEN, CLOSE
  - price               (float64)   Geometric Brownian motion around realistic baselines
  - volume              (int32)     Log-normal, 1 to 1M shares
  - bid_price           (float64)   price - spread
  - ask_price           (float64)   price + spread
  - spread_bps          (float32)   Bid-ask spread in basis points
  - market_cap_tier     (dict)      Mega, Large, Mid, Small, Micro
  - sector              (dict)      Technology, Healthcare, Finance, Energy, Consumer, Industrial
  - is_after_hours      (bool)      ~15% of ticks
  - tick_timestamp      (timestamp) Microsecond precision, monotonic

Memory strategy: Chunked streaming. Peak RAM ~120MB.
"""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pa_csv
import time
import os
from tqdm import tqdm

TOTAL_ROWS  = 200_000_000
CHUNK_SIZE  = 500_000
PARQUET_OUT = "data/financial_ticks_200m.parquet"
CSV_OUT     = "data/financial_ticks_200m.csv"
RANDOM_SEED = 42

EXCHANGES = ["NYSE", "NASDAQ", "LSE", "TSE", "HKEX"]
TICK_TYPES = ["TRADE", "BID", "ASK", "OPEN", "CLOSE"]
CAP_TIERS = ["Mega", "Large", "Mid", "Small", "Micro"]
SECTORS   = ["Technology", "Healthcare", "Finance", "Energy", "Consumer", "Industrial"]

EX_WEIGHTS   = [0.30, 0.30, 0.15, 0.15, 0.10]
TICK_WEIGHTS = [0.50, 0.20, 0.20, 0.05, 0.05]
CAP_WEIGHTS  = [0.15, 0.25, 0.30, 0.20, 0.10]
SEC_WEIGHTS  = [0.25, 0.18, 0.20, 0.12, 0.15, 0.10]

SCHEMA = pa.schema([
    pa.field("tick_id",         pa.int64()),
    pa.field("symbol",          pa.dictionary(pa.int16(), pa.utf8())),
    pa.field("exchange",        pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("tick_type",       pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("price",           pa.float64()),
    pa.field("volume",          pa.int32()),
    pa.field("bid_price",       pa.float64()),
    pa.field("ask_price",       pa.float64()),
    pa.field("spread_bps",      pa.float32()),
    pa.field("market_cap_tier", pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("sector",          pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("is_after_hours",  pa.bool_()),
    pa.field("tick_timestamp",  pa.timestamp("us")),
])

def _make_symbols(rng, n=500):
    consonants = list("BCDFGHJKLMNPQRSTVWXYZ")
    vowels = list("AEIOU")
    syms = set()
    while len(syms) < n:
        length = rng.choice([3, 4])
        if length == 3:
            s = rng.choice(consonants) + rng.choice(vowels) + rng.choice(consonants)
        else:
            s = rng.choice(consonants) + rng.choice(vowels) + rng.choice(consonants) + rng.choice(vowels)
        syms.add(s)
    return sorted(syms)

def _make_base_prices(rng, symbols):
    """Assign a realistic base price to each symbol using log-normal."""
    return np.clip(rng.lognormal(mean=4.0, sigma=1.0, size=len(symbols)), 1.0, 5000.0)

def generate_chunk(rng, symbols, base_prices, start_id, base_ts_us, n):
    ids = np.arange(start_id, start_id + n, dtype=np.int64)

    sym_idx = rng.integers(0, len(symbols), size=n, dtype=np.int16)
    ex_idx  = rng.choice(len(EXCHANGES), size=n, p=EX_WEIGHTS).astype(np.int8)
    tt_idx  = rng.choice(len(TICK_TYPES), size=n, p=TICK_WEIGHTS).astype(np.int8)
    cap_idx = rng.choice(len(CAP_TIERS), size=n, p=CAP_WEIGHTS).astype(np.int8)
    sec_idx = rng.choice(len(SECTORS), size=n, p=SEC_WEIGHTS).astype(np.int8)

    # GBM-like price: base_price * (1 + small normal jitter)
    bases  = base_prices[sym_idx]
    jitter = rng.normal(0, 0.002, size=n)
    price  = (bases * (1 + jitter)).astype(np.float64)
    price  = np.maximum(price, 0.01)

    # Spread in basis points: tighter for mega caps, wider for micro
    spread_bps = np.where(cap_idx == 0, rng.uniform(0.5, 3, n),
                 np.where(cap_idx == 1, rng.uniform(1, 5, n),
                 np.where(cap_idx == 2, rng.uniform(2, 10, n),
                 np.where(cap_idx == 3, rng.uniform(5, 25, n),
                                        rng.uniform(10, 50, n))))).astype(np.float32)

    half_spread = price * (spread_bps / 10000.0 / 2.0)
    bid_price = (price - half_spread).astype(np.float64)
    ask_price = (price + half_spread).astype(np.float64)

    volume = np.clip(rng.lognormal(mean=7, sigma=2, size=n), 1, 1_000_000).astype(np.int32)
    is_after = rng.random(size=n) < 0.15

    intervals = rng.integers(1, 500, size=n, dtype=np.int64).cumsum()
    timestamps = base_ts_us + intervals
    new_base = int(timestamps[-1])

    batch = pa.RecordBatch.from_arrays([
        pa.array(ids, type=pa.int64()),
        pa.DictionaryArray.from_arrays(pa.array(sym_idx, type=pa.int16()), pa.array(symbols)),
        pa.DictionaryArray.from_arrays(pa.array(ex_idx, type=pa.int8()), pa.array(EXCHANGES)),
        pa.DictionaryArray.from_arrays(pa.array(tt_idx, type=pa.int8()), pa.array(TICK_TYPES)),
        pa.array(price, type=pa.float64()),
        pa.array(volume, type=pa.int32()),
        pa.array(bid_price, type=pa.float64()),
        pa.array(ask_price, type=pa.float64()),
        pa.array(spread_bps, type=pa.float32()),
        pa.DictionaryArray.from_arrays(pa.array(cap_idx, type=pa.int8()), pa.array(CAP_TIERS)),
        pa.DictionaryArray.from_arrays(pa.array(sec_idx, type=pa.int8()), pa.array(SECTORS)),
        pa.array(is_after, type=pa.bool_()),
        pa.array(timestamps, type=pa.timestamp("us")),
    ], schema=SCHEMA)
    return batch, new_base

def write_files(rng, symbols, base_prices):
    n_chunks = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts  = int(time.time() * 1_000_000) - TOTAL_ROWS * 250

    writer = None
    rows = 0
    t0 = time.perf_counter()
    try:
        for _ in tqdm(range(n_chunks), desc="Parquet", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng, symbols, base_prices, rows, base_ts, n)
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
    sym2 = _make_symbols(rng2)
    bp2  = _make_base_prices(rng2, sym2)
    rows = 0
    base_ts = int(time.time() * 1_000_000) - TOTAL_ROWS * 250
    t0 = time.perf_counter()
    header = False
    with open(CSV_OUT, "wb", buffering=16*1024*1024) as f:
        for _ in tqdm(range(n_chunks), desc="CSV    ", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng2, sym2, bp2, rows, base_ts, n)
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
    print("  Financial Market Tick Data Generator")
    print(f"  Rows: {TOTAL_ROWS:,} | Chunk: {CHUNK_SIZE:,}")
    print("=" * 60)
    os.makedirs("data", exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    symbols = _make_symbols(rng)
    base_prices = _make_base_prices(rng, symbols)
    write_files(rng, symbols, base_prices)
    print("  Done.")

if __name__ == "__main__":
    main()
