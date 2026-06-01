"""
gen_ecommerce.py
-----------------
Generates a hyperrealistic e-commerce transactions dataset.

Schema (14 columns):
  - order_id            (int64)     Unique sequential order ID
  - customer_id         (int32)     ~2M unique customers
  - product_category    (dict)      Electronics, Clothing, Home, Books, Sports, Beauty, Food, Toys
  - product_sku         (dict)      ~50,000 unique SKUs
  - unit_price           (float32)  $0.99 to $2,999.99 (log-normal)
  - quantity            (int16)     1-20
  - discount_pct        (float32)   0.0 to 0.50 (most are 0)
  - payment_method      (dict)      Credit, Debit, PayPal, ApplePay, Crypto
  - shipping_region     (dict)      US-East, US-West, EU-West, EU-East, APAC, LATAM, MEA
  - is_returned         (bool)      ~8% return rate
  - customer_lifetime_orders (int32) Power-law, 1-500
  - session_duration_sec (float32)  Browsing time before purchase
  - device_type         (dict)      Mobile, Desktop, Tablet
  - order_timestamp     (timestamp) Monotonically increasing

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
PARQUET_OUT = "data/ecommerce_100m.parquet"
CSV_OUT     = "data/ecommerce_100m.csv"
RANDOM_SEED = 42

CATEGORIES     = ["Electronics", "Clothing", "Home", "Books", "Sports", "Beauty", "Food", "Toys"]
PAYMENT        = ["Credit", "Debit", "PayPal", "ApplePay", "Crypto"]
REGIONS        = ["US-East", "US-West", "EU-West", "EU-East", "APAC", "LATAM", "MEA"]
DEVICES        = ["Mobile", "Desktop", "Tablet"]

CAT_WEIGHTS    = [0.22, 0.20, 0.15, 0.12, 0.10, 0.09, 0.07, 0.05]
PAY_WEIGHTS    = [0.35, 0.25, 0.20, 0.12, 0.08]
REGION_WEIGHTS = [0.25, 0.20, 0.18, 0.12, 0.13, 0.07, 0.05]
DEVICE_WEIGHTS = [0.55, 0.35, 0.10]

SCHEMA = pa.schema([
    pa.field("order_id",                  pa.int64()),
    pa.field("customer_id",               pa.int32()),
    pa.field("product_category",          pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("product_sku",               pa.dictionary(pa.int16(), pa.utf8())),
    pa.field("unit_price",                pa.float32()),
    pa.field("quantity",                  pa.int16()),
    pa.field("discount_pct",              pa.float32()),
    pa.field("payment_method",            pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("shipping_region",           pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("is_returned",               pa.bool_()),
    pa.field("customer_lifetime_orders",  pa.int32()),
    pa.field("session_duration_sec",      pa.float32()),
    pa.field("device_type",               pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("order_timestamp",           pa.timestamp("ms")),
])

def _make_sku_pool(rng, n=50_000):
    prefixes = ["SKU", "PRD", "ITM", "ART"]
    return [f"{rng.choice(prefixes)}-{rng.integers(100000, 999999)}" for _ in range(n)]

def generate_chunk(rng, sku_pool, start_id, base_ts_ms, n):
    order_ids = np.arange(start_id, start_id + n, dtype=np.int64)
    customer_ids = rng.integers(1, 2_000_001, size=n, dtype=np.int32)

    cat_idx = rng.choice(len(CATEGORIES), size=n, p=CAT_WEIGHTS).astype(np.int8)
    sku_idx = rng.integers(0, len(sku_pool), size=n, dtype=np.int16)
    pay_idx = rng.choice(len(PAYMENT), size=n, p=PAY_WEIGHTS).astype(np.int8)
    reg_idx = rng.choice(len(REGIONS), size=n, p=REGION_WEIGHTS).astype(np.int8)
    dev_idx = rng.choice(len(DEVICES), size=n, p=DEVICE_WEIGHTS).astype(np.int8)

    unit_price = np.clip(rng.lognormal(mean=3.0, sigma=1.2, size=n), 0.99, 2999.99).astype(np.float32)
    quantity = rng.integers(1, 21, size=n, dtype=np.int16)

    discount = np.zeros(n, dtype=np.float32)
    has_discount = rng.random(size=n) < 0.25
    discount[has_discount] = np.clip(rng.beta(1.5, 5, size=has_discount.sum()), 0.01, 0.50).astype(np.float32)

    is_returned = rng.random(size=n) < 0.08

    clt_orders = np.clip(rng.pareto(1.5, size=n) + 1, 1, 500).astype(np.int32)
    session_dur = np.clip(rng.lognormal(mean=5.5, sigma=1.0, size=n), 5, 7200).astype(np.float32)

    intervals = rng.integers(50, 500, size=n, dtype=np.int64).cumsum()
    timestamps = base_ts_ms + intervals
    new_base = int(timestamps[-1])

    batch = pa.RecordBatch.from_arrays([
        pa.array(order_ids, type=pa.int64()),
        pa.array(customer_ids, type=pa.int32()),
        pa.DictionaryArray.from_arrays(pa.array(cat_idx, type=pa.int8()), pa.array(CATEGORIES)),
        pa.DictionaryArray.from_arrays(pa.array(sku_idx, type=pa.int16()), pa.array(sku_pool)),
        pa.array(unit_price, type=pa.float32()),
        pa.array(quantity, type=pa.int16()),
        pa.array(discount, type=pa.float32()),
        pa.DictionaryArray.from_arrays(pa.array(pay_idx, type=pa.int8()), pa.array(PAYMENT)),
        pa.DictionaryArray.from_arrays(pa.array(reg_idx, type=pa.int8()), pa.array(REGIONS)),
        pa.array(is_returned, type=pa.bool_()),
        pa.array(clt_orders, type=pa.int32()),
        pa.array(session_dur, type=pa.float32()),
        pa.DictionaryArray.from_arrays(pa.array(dev_idx, type=pa.int8()), pa.array(DEVICES)),
        pa.array(timestamps, type=pa.timestamp("ms")),
    ], schema=SCHEMA)
    return batch, new_base

def write_files(rng, sku_pool, out_parquet, out_csv):
    n_chunks = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts  = int(time.time() * 1000) - TOTAL_ROWS * 300

    # Parquet
    writer = None
    rows = 0
    t0 = time.perf_counter()
    try:
        for _ in tqdm(range(n_chunks), desc="Parquet", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng, sku_pool, rows, base_ts, n)
            if writer is None:
                writer = pq.ParquetWriter(out_parquet, schema=SCHEMA, compression="snappy", use_dictionary=True, write_statistics=True)
            writer.write_batch(batch)
            rows += n
    finally:
        if writer: writer.close()
    p_time = time.perf_counter() - t0
    p_size = os.path.getsize(out_parquet) / (1024**2)
    print(f"  Parquet: {rows:,} rows | {p_size:.0f} MB | {p_time:.1f}s")

    # CSV
    rng2 = np.random.default_rng(RANDOM_SEED)
    sku2 = _make_sku_pool(rng2)
    rows = 0
    base_ts = int(time.time() * 1000) - TOTAL_ROWS * 300
    t0 = time.perf_counter()
    header = False
    with open(out_csv, "wb", buffering=16*1024*1024) as f:
        for _ in tqdm(range(n_chunks), desc="CSV    ", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng2, sku2, rows, base_ts, n)
            tbl = pa.Table.from_batches([batch])
            pa_csv.write_csv(tbl, f, write_options=pa_csv.WriteOptions(include_header=not header))
            header = True
            rows += n
    c_time = time.perf_counter() - t0
    c_size = os.path.getsize(out_csv) / (1024**2)
    print(f"  CSV:     {rows:,} rows | {c_size:.0f} MB | {c_time:.1f}s")
    print(f"  Ratio:   {c_size/p_size:.1f}x (CSV vs Parquet)")

def main():
    print("=" * 60)
    print("  E-Commerce Transactions Generator")
    print(f"  Rows: {TOTAL_ROWS:,} | Chunk: {CHUNK_SIZE:,}")
    print("=" * 60)
    os.makedirs("data", exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    sku_pool = _make_sku_pool(rng)
    write_files(rng, sku_pool, PARQUET_OUT, CSV_OUT)
    print("  Done.")

if __name__ == "__main__":
    main()
