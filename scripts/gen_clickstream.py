"""
gen_clickstream.py
------------------
Generates realistic web analytics clickstream data.

Schema (14 columns):
  - event_id            (int64)     Unique sequential event ID
  - session_id          (dict)      ~5M unique sessions
  - user_id             (dict)      ~1M unique users (some null/anonymous)
  - event_type          (dict)      page_view, click, scroll, add_to_cart, purchase, bounce
  - page_url            (dict)      ~500 unique URLs
  - referrer_url        (dict)      ~100 referrers (Google, Facebook, Direct, etc.)
  - user_agent          (dict)      Browser and OS combinations
  - device_category     (dict)      Mobile, Desktop, Tablet, SmartTV
  - geo_country         (dict)      Country codes (US, UK, IN, CA, etc.)
  - load_time_ms        (int16)     Page load time in milliseconds
  - scroll_depth_pct    (int8)      0 to 100
  - is_bounced          (bool)      Did the user leave immediately?
  - conversion_value    (float32)   Value if purchase event, otherwise 0
  - event_timestamp     (timestamp) Millisecond precision, monotonic

Memory strategy: Chunked streaming via PyArrow. Peak RAM ~150MB.
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
PARQUET_OUT = "data/clickstream_100m.parquet"
CSV_OUT     = "data/clickstream_100m.csv"
RANDOM_SEED = 42

EVENT_TYPES = ["page_view", "click", "scroll", "add_to_cart", "purchase", "bounce"]
DEVICES     = ["Mobile", "Desktop", "Tablet", "SmartTV"]
COUNTRIES   = ["US", "IN", "UK", "CA", "DE", "FR", "JP", "BR", "AU", "IT"]
REFERRERS   = ["Direct", "google.com", "facebook.com", "t.co", "bing.com", "reddit.com"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

EV_WEIGHTS   = [0.45, 0.25, 0.15, 0.08, 0.02, 0.05]
DEV_WEIGHTS  = [0.60, 0.30, 0.08, 0.02]
CTY_WEIGHTS  = [0.35, 0.20, 0.10, 0.08, 0.07, 0.05, 0.05, 0.04, 0.03, 0.03]
REF_WEIGHTS  = [0.30, 0.40, 0.15, 0.05, 0.05, 0.05]
UA_WEIGHTS   = [0.40, 0.15, 0.30, 0.10, 0.05]

SCHEMA = pa.schema([
    pa.field("event_id",            pa.int64()),
    pa.field("session_id",          pa.dictionary(pa.int32(), pa.utf8())),
    pa.field("user_id",             pa.dictionary(pa.int32(), pa.utf8())),
    pa.field("event_type",          pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("page_url",            pa.dictionary(pa.int16(), pa.utf8())),
    pa.field("referrer_url",        pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("user_agent",          pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("device_category",     pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("geo_country",         pa.dictionary(pa.int8(), pa.utf8())),
    pa.field("load_time_ms",        pa.int16()),
    pa.field("scroll_depth_pct",    pa.int8()),
    pa.field("is_bounced",          pa.bool_()),
    pa.field("conversion_value",    pa.float32()),
    pa.field("event_timestamp",     pa.timestamp("ms")),
])

def _make_urls(rng, n=500):
    categories = ["/products/", "/blog/", "/category/", "/promo/"]
    return ["/"] + [f"{rng.choice(categories)}{rng.integers(1000, 9999)}" for _ in range(n - 1)]

def _make_ids(rng, prefix, n):
    return [f"{prefix}_{i:07x}" for i in range(n)]

def generate_chunk(rng, sessions, users, urls, start_id, base_ts_ms, n):
    ids = np.arange(start_id, start_id + n, dtype=np.int64)

    sess_idx = rng.integers(0, len(sessions), size=n, dtype=np.int32)
    user_idx = rng.integers(0, len(users), size=n, dtype=np.int32)
    
    ev_idx  = rng.choice(len(EVENT_TYPES), size=n, p=EV_WEIGHTS).astype(np.int8)
    url_idx = rng.integers(0, len(urls), size=n, dtype=np.int16)
    ref_idx = rng.choice(len(REFERRERS), size=n, p=REF_WEIGHTS).astype(np.int8)
    ua_idx  = rng.choice(len(USER_AGENTS), size=n, p=UA_WEIGHTS).astype(np.int8)
    dev_idx = rng.choice(len(DEVICES), size=n, p=DEV_WEIGHTS).astype(np.int8)
    cty_idx = rng.choice(len(COUNTRIES), size=n, p=CTY_WEIGHTS).astype(np.int8)

    load_time = np.clip(rng.lognormal(mean=6.5, sigma=0.8, size=n), 100, 15000).astype(np.int16)
    scroll    = rng.integers(0, 101, size=n, dtype=np.int8)
    
    is_bounce = ev_idx == EVENT_TYPES.index("bounce")
    
    # Only purchases have value
    conv_val = np.zeros(n, dtype=np.float32)
    is_purchase = ev_idx == EVENT_TYPES.index("purchase")
    conv_val[is_purchase] = np.clip(rng.lognormal(mean=4.0, sigma=1.0, size=is_purchase.sum()), 5.0, 5000.0).astype(np.float32)

    intervals = rng.integers(10, 5000, size=n, dtype=np.int64).cumsum()
    timestamps = base_ts_ms + intervals
    new_base = int(timestamps[-1])

    batch = pa.RecordBatch.from_arrays([
        pa.array(ids, type=pa.int64()),
        pa.DictionaryArray.from_arrays(pa.array(sess_idx, type=pa.int32()), pa.array(sessions)),
        pa.DictionaryArray.from_arrays(pa.array(user_idx, type=pa.int32()), pa.array(users)),
        pa.DictionaryArray.from_arrays(pa.array(ev_idx, type=pa.int8()), pa.array(EVENT_TYPES)),
        pa.DictionaryArray.from_arrays(pa.array(url_idx, type=pa.int16()), pa.array(urls)),
        pa.DictionaryArray.from_arrays(pa.array(ref_idx, type=pa.int8()), pa.array(REFERRERS)),
        pa.DictionaryArray.from_arrays(pa.array(ua_idx, type=pa.int8()), pa.array(USER_AGENTS)),
        pa.DictionaryArray.from_arrays(pa.array(dev_idx, type=pa.int8()), pa.array(DEVICES)),
        pa.DictionaryArray.from_arrays(pa.array(cty_idx, type=pa.int8()), pa.array(COUNTRIES)),
        pa.array(load_time, type=pa.int16()),
        pa.array(scroll, type=pa.int8()),
        pa.array(is_bounce, type=pa.bool_()),
        pa.array(conv_val, type=pa.float32()),
        pa.array(timestamps, type=pa.timestamp("ms")),
    ], schema=SCHEMA)
    return batch, new_base

def write_files(rng, sessions, users, urls):
    n_chunks = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts  = int(time.time() * 1000) - TOTAL_ROWS * 50

    writer = None
    rows = 0
    t0 = time.perf_counter()
    try:
        for _ in tqdm(range(n_chunks), desc="Parquet", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng, sessions, users, urls, rows, base_ts, n)
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
    sess2 = _make_ids(rng2, "s", 5_000_000)
    users2 = _make_ids(rng2, "u", 1_000_000)
    urls2 = _make_urls(rng2)
    
    rows = 0
    base_ts = int(time.time() * 1000) - TOTAL_ROWS * 50
    t0 = time.perf_counter()
    header = False
    with open(CSV_OUT, "wb", buffering=16*1024*1024) as f:
        for _ in tqdm(range(n_chunks), desc="CSV    ", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows)
            batch, base_ts = generate_chunk(rng2, sess2, users2, urls2, rows, base_ts, n)
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
    print("  Clickstream Analytics Data Generator")
    print(f"  Rows: {TOTAL_ROWS:,} | Chunk: {CHUNK_SIZE:,}")
    print("=" * 60)
    os.makedirs("data", exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    sessions = _make_ids(rng, "s", 5_000_000)
    users = _make_ids(rng, "u", 1_000_000)
    urls = _make_urls(rng)
    write_files(rng, sessions, users, urls)
    print("  Done.")

if __name__ == "__main__":
    main()
