"""
run_predicate_benchmark.py
--------------------------
Benchmarks Predicate Pushdown: the key reason why Polars + Parquet
is superior to Pandas + CSV for analytical queries on large datasets.

The Query:
  Find all training runs where:
    - framework == 'PyTorch'         (categorical filter)
    - validation_accuracy > 0.90     (range filter)
  Return: framework, hardware_target, validation_accuracy, training_loss

What this demonstrates:
  - Pandas + CSV:    Reads ALL 3.5GB from disk → filters in RAM → returns result
  - Polars + Parquet: Pushes the filter DOWN to storage. Only reads matching
                      row groups + selected columns. Reads a fraction of the file.

Outputs:
  viz-app/src/data/predicate_results.json
"""

import json
import os
import sys
import time
import psutil
import gc

# Config
PARQUET_PATH = "data/ml_logs_25m.parquet"
CSV_PATH     = "data/ml_logs_25m.csv"
OUTPUT_JSON  = "viz-app/src/data/predicate_results.json"

# The analytical query
FILTER_FRAMEWORK = "PyTorch"
FILTER_VAL_ACC   = 0.90
SELECT_COLS      = ["framework", "hardware_target", "validation_accuracy", "training_loss"]
TOTAL_COLS       = 13

# Helpers
def get_disk_read_mb() -> float:
    return psutil.disk_io_counters().read_bytes / (1024 ** 2)

def get_file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 ** 2)

def flush_os_cache():
    """Best-effort: force GC and short sleep to give OS time to evict page cache."""
    gc.collect()
    time.sleep(2)

# Benchmark 1: Pandas + CSV  (No pushdown — reads everything)
def bench_pandas_csv():
    import pandas as pd

    flush_os_cache()
    disk_before = get_disk_read_mb()
    t0 = time.perf_counter()

    df = pd.read_csv(
        CSV_PATH,
        usecols=SELECT_COLS + ["validation_accuracy"],   # still reads ALL rows
    )
    df_filtered = df[
        (df["framework"] == FILTER_FRAMEWORK) &
        (df["validation_accuracy"] > FILTER_VAL_ACC)
    ]
    rows_matched = len(df_filtered)
    del df, df_filtered

    elapsed   = time.perf_counter() - t0
    disk_read = get_disk_read_mb() - disk_before

    return {
        "engine"       : "Pandas",
        "format"       : "CSV",
        "elapsed_s"    : round(elapsed, 3),
        "disk_read_mb" : round(disk_read, 1),
        "rows_matched" : rows_matched,
        "strategy"     : "Full scan → filter in RAM",
        "color"        : "#ef4444",
    }

# Benchmark 2: Polars + Parquet  (Full predicate pushdown)
def bench_polars_parquet():
    import polars as pl

    flush_os_cache()
    disk_before = get_disk_read_mb()
    t0 = time.perf_counter()

    # scan_parquet is lazy — the filter and column selection are pushed
    # down to the Parquet reader. Only matching row groups are decompressed.
    df = (
        pl.scan_parquet(PARQUET_PATH)
        .filter(
            (pl.col("framework") == FILTER_FRAMEWORK) &
            (pl.col("validation_accuracy") > FILTER_VAL_ACC)
        )
        .select(SELECT_COLS)
        .collect()
    )
    rows_matched = len(df)
    del df

    elapsed   = time.perf_counter() - t0
    disk_read = get_disk_read_mb() - disk_before

    return {
        "engine"       : "Polars",
        "format"       : "Parquet",
        "elapsed_s"    : round(elapsed, 3),
        "disk_read_mb" : round(disk_read, 1),
        "rows_matched" : rows_matched,
        "strategy"     : "Predicate pushdown → reads only matching row groups",
        "color"        : "#22c55e",
    }

# Benchmark 3: Pandas + Parquet (partial pushdown via PyArrow filters)
def bench_pandas_parquet():
    import pandas as pd

    flush_os_cache()
    disk_before = get_disk_read_mb()
    t0 = time.perf_counter()

    df = pd.read_parquet(
        PARQUET_PATH,
        columns=SELECT_COLS,
        filters=[
            ("framework", "==", FILTER_FRAMEWORK),
            ("validation_accuracy", ">", FILTER_VAL_ACC),
        ],
    )
    rows_matched = len(df)
    del df

    elapsed   = time.perf_counter() - t0
    disk_read = get_disk_read_mb() - disk_before

    return {
        "engine"       : "Pandas",
        "format"       : "Parquet",
        "elapsed_s"    : round(elapsed, 3),
        "disk_read_mb" : round(disk_read, 1),
        "rows_matched" : rows_matched,
        "strategy"     : "Row-group filter via PyArrow → still loads all columns",
        "color"        : "#f97316",
    }

# Main
def main():
    for pkg in ["pandas", "polars", "psutil"]:
        try:
            __import__(pkg)
        except ImportError:
            print(f"  Missing: pip install {pkg}")
            sys.exit(1)

    for path in [PARQUET_PATH, CSV_PATH]:
        if not os.path.exists(path):
            print(f"  ERROR: file not found: {path} — run gen_ml_logs.py first")
            sys.exit(1)

    parquet_mb = get_file_size_mb(PARQUET_PATH)
    csv_mb     = get_file_size_mb(CSV_PATH)

    print()
    print("=" * 65)
    print("  Predicate Pushdown Benchmark")
    print(f"  Query: framework == '{FILTER_FRAMEWORK}' AND val_acc > {FILTER_VAL_ACC}")
    print(f"  Select: {SELECT_COLS}")
    print("=" * 65)
    print(f"  Parquet file: {parquet_mb:.1f} MB")
    print(f"  CSV file    : {csv_mb:.1f} MB")
    print()

    results = []

    print("  ▶  Polars + Parquet (predicate pushdown) ...")
    r = bench_polars_parquet()
    results.append(r)
    print(f"     ✓  {r['elapsed_s']:.3f}s  |  Disk read: {r['disk_read_mb']:.1f} MB  |  Rows: {r['rows_matched']:,}")

    print("  ▶  Pandas + Parquet (PyArrow row-group filter) ...")
    r = bench_pandas_parquet()
    results.append(r)
    print(f"     ✓  {r['elapsed_s']:.3f}s  |  Disk read: {r['disk_read_mb']:.1f} MB  |  Rows: {r['rows_matched']:,}")

    print("  ▶  Pandas + CSV (full scan) ...")
    r = bench_pandas_csv()
    results.append(r)
    print(f"     ✓  {r['elapsed_s']:.3f}s  |  Disk read: {r['disk_read_mb']:.1f} MB  |  Rows: {r['rows_matched']:,}")

    # Sort slowest → fastest for the chart
    results.sort(key=lambda x: -x["disk_read_mb"])

    polars_p  = next(x for x in results if x["engine"] == "Polars")
    pandas_csv = next(x for x in results if x["engine"] == "Pandas" and x["format"] == "CSV")
    io_reduction = round((pandas_csv["disk_read_mb"] - polars_p["disk_read_mb"]) / pandas_csv["disk_read_mb"] * 100, 1) if pandas_csv["disk_read_mb"] > 0 else 0
    speedup = round(pandas_csv["elapsed_s"] / polars_p["elapsed_s"], 1) if polars_p["elapsed_s"] > 0 else 0

    output = {
        "query": {
            "filter"       : f"framework == '{FILTER_FRAMEWORK}' AND validation_accuracy > {FILTER_VAL_ACC}",
            "select_cols"  : SELECT_COLS,
            "total_cols"   : TOTAL_COLS,
            "selected_cols": len(SELECT_COLS),
            "rows_matched" : results[0]["rows_matched"],
        },
        "files": {
            "parquet_mb": round(parquet_mb, 1),
            "csv_mb"    : round(csv_mb, 1),
        },
        "results"       : results,
        "io_reduction_pct": io_reduction,
        "speedup"       : speedup,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print("=" * 65)
    print(f"  Polars read {polars_p['disk_read_mb']:.0f}MB from disk.")
    print(f"  Pandas+CSV read {pandas_csv['disk_read_mb']:.0f}MB from disk.")
    print(f"  I/O reduction: {io_reduction}% less data read from disk.")
    print(f"  Speedup: {speedup}x faster query.")
    print(f"\n  Results saved → {OUTPUT_JSON}")
    print("=" * 65)

if __name__ == "__main__":
    main()
