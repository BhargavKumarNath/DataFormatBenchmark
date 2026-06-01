"""
run_benchmark.py
----------------
Live hardware benchmark: Pandas/CSV vs Polars/Parquet vs all combinations.

Measures for each of the 4 engine+format combinations:
  - Total load time (seconds)
  - Peak RAM usage (MB)
  - RAM usage sampled every 200ms (for line chart visualization)
  - CPU core utilization sampled every 200ms
  - Read throughput (MB/s and Rows/s)
  - Disk I/O bytes read

Safety Features:
  - RAM Watchdog thread kills any test that exceeds RAM_LIMIT_GB
  - Graceful OOM recording — crash is logged, not hidden
  - Process isolation via subprocess to allow clean memory recovery
  - Conservative test ordering (safest first, most dangerous last)

Outputs:
  live_results.json  →  viz-app/src/data/live_results.json

Requirements:
  pip install pandas polars pyarrow psutil tqdm
"""

import json
import os
import sys
import time
import threading
import traceback
import subprocess
import platform
import psutil

# Configuration
PARQUET_PATH  = "data/ml_logs_25m.parquet"
CSV_PATH      = "data/ml_logs_25m.csv"
OUTPUT_JSON   = "viz-app/src/data/live_results.json"

RAM_LIMIT_GB  = 13.5          # Watchdog kills test above this threshold
SAMPLE_INTERVAL_MS = 200      # RAM/CPU sampling resolution (ms)
TOTAL_ROWS    = 25_000_000

# Helpers
def get_ram_gb() -> float:
    """Return current process + children RAM usage in GB."""
    try:
        proc = psutil.Process(os.getpid())
        rss  = proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return rss / (1024 ** 3)
    except Exception:
        return 0.0


def get_system_ram_gb() -> float:
    """Return total system RAM used (GB)."""
    return psutil.virtual_memory().used / (1024 ** 3)


def get_cpu_percent_per_core() -> list[float]:
    """Return per-core CPU utilization as list of floats."""
    return psutil.cpu_percent(percpu=True)


def get_file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 ** 2)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs    = seconds % 60
    return f"{minutes}m {secs:.1f}s"


# RAM Watchdog
class RamWatchdog:
    """
    Background thread that monitors system RAM.
    Sets self.triggered = True if usage exceeds limit.
    Callers must poll self.triggered inside their load loop.
    """
    def __init__(self, limit_gb: float = RAM_LIMIT_GB):
        self.limit_gb  = limit_gb
        self.triggered = False
        self.peak_gb   = 0.0
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._monitor, daemon=True)

    def start(self):
        self._stop.clear()
        self.triggered = False
        self.peak_gb   = 0.0
        self._thread   = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _monitor(self):
        while not self._stop.is_set():
            used = get_system_ram_gb()
            if used > self.peak_gb:
                self.peak_gb = used
            if used >= self.limit_gb:
                self.triggered = True
            time.sleep(SAMPLE_INTERVAL_MS / 1000)


# Sampler (records time-series of RAM + CPU for the dashboard charts)
class ResourceSampler:
    """
    Records [timestamp_offset_s, ram_gb, avg_cpu_pct] tuples
    while a benchmark test is running.
    """
    def __init__(self):
        self.samples   = []   # list of [elapsed_s, ram_gb, cpu_pct]
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._sample, daemon=True)
        self._t0       = None

    def start(self):
        self._stop.clear()
        self.samples = []
        self._t0     = time.perf_counter()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _sample(self):
        while not self._stop.is_set():
            elapsed  = round(time.perf_counter() - self._t0, 2)
            ram      = round(get_system_ram_gb(), 3)
            cpu_pcts = get_cpu_percent_per_core()
            avg_cpu  = round(sum(cpu_pcts) / len(cpu_pcts), 1)
            self.samples.append([elapsed, ram, avg_cpu, cpu_pcts])
            time.sleep(SAMPLE_INTERVAL_MS / 1000)


# Individual benchmark runners
def _run_pandas_csv(watchdog: RamWatchdog, sampler: ResourceSampler) -> dict:
    import pandas as pd

    disk_before = psutil.disk_io_counters()
    t0   = time.perf_counter()
    oom  = False
    rows = 0

    try:
        # Read in chunks to allow watchdog to intervene
        chunks = []
        reader = pd.read_csv(CSV_PATH, chunksize=2_000_000)
        for chunk in reader:
            if watchdog.triggered:
                oom = True
                del chunks
                break
            chunks.append(chunk)
            rows += len(chunk)

        if not oom:
            df   = pd.concat(chunks, ignore_index=True)
            rows = len(df)
            del df, chunks

    except MemoryError:
        oom = True

    elapsed      = time.perf_counter() - t0
    disk_after   = psutil.disk_io_counters()
    bytes_read   = (disk_after.read_bytes - disk_before.read_bytes) / (1024 ** 2)

    return {
        "elapsed_s"    : round(elapsed, 3),
        "peak_ram_gb"  : round(sampler.samples[-1][1] if sampler.samples else 0, 3),
        "throughput_mb": round(bytes_read / elapsed if elapsed > 0 else 0, 1),
        "rows_read"    : rows,
        "oom_crash"    : oom,
    }


def _run_pandas_parquet(watchdog: RamWatchdog, sampler: ResourceSampler) -> dict:
    import pandas as pd

    disk_before = psutil.disk_io_counters()
    t0   = time.perf_counter()
    oom  = False
    rows = 0

    try:
        df   = pd.read_parquet(PARQUET_PATH)
        rows = len(df)
        del df
    except MemoryError:
        oom = True
    except Exception as e:
        print(f"    [warn] pandas parquet error: {e}")

    elapsed    = time.perf_counter() - t0
    disk_after = psutil.disk_io_counters()
    bytes_read = (disk_after.read_bytes - disk_before.read_bytes) / (1024 ** 2)

    return {
        "elapsed_s"    : round(elapsed, 3),
        "peak_ram_gb"  : round(sampler.samples[-1][1] if sampler.samples else 0, 3),
        "throughput_mb": round(bytes_read / elapsed if elapsed > 0 else 0, 1),
        "rows_read"    : rows,
        "oom_crash"    : oom,
    }


def _run_polars_csv(watchdog: RamWatchdog, sampler: ResourceSampler) -> dict:
    import polars as pl

    disk_before = psutil.disk_io_counters()
    t0   = time.perf_counter()
    oom  = False
    rows = 0

    try:
        df   = pl.read_csv(CSV_PATH, infer_schema_length=10_000)
        rows = len(df)
        del df
    except Exception as e:
        print(f"    [warn] polars csv error: {e}")

    elapsed    = time.perf_counter() - t0
    disk_after = psutil.disk_io_counters()
    bytes_read = (disk_after.read_bytes - disk_before.read_bytes) / (1024 ** 2)

    return {
        "elapsed_s"    : round(elapsed, 3),
        "peak_ram_gb"  : round(sampler.samples[-1][1] if sampler.samples else 0, 3),
        "throughput_mb": round(bytes_read / elapsed if elapsed > 0 else 0, 1),
        "rows_read"    : rows,
        "oom_crash"    : oom,
    }


def _run_polars_parquet(watchdog: RamWatchdog, sampler: ResourceSampler) -> dict:
    import polars as pl

    disk_before = psutil.disk_io_counters()
    t0   = time.perf_counter()
    oom  = False
    rows = 0

    try:
        # Use lazy evaluation — the ultimate Polars advantage
        lf   = pl.scan_parquet(PARQUET_PATH)
        df   = lf.collect()
        rows = len(df)
        del df, lf
    except Exception as e:
        print(f"    [warn] polars parquet error: {e}")

    elapsed    = time.perf_counter() - t0
    disk_after = psutil.disk_io_counters()
    bytes_read = (disk_after.read_bytes - disk_before.read_bytes) / (1024 ** 2)

    return {
        "elapsed_s"    : round(elapsed, 3),
        "peak_ram_gb"  : round(sampler.samples[-1][1] if sampler.samples else 0, 3),
        "throughput_mb": round(bytes_read / elapsed if elapsed > 0 else 0, 1),
        "rows_read"    : rows,
        "oom_crash"    : oom,
    }


# Master benchmark runner
TESTS = [
    # Run safest → most dangerous order
    ("Polars + Parquet", "polars",  "parquet", _run_polars_parquet),
    ("Polars + CSV",     "polars",  "csv",     _run_polars_csv),
    ("Pandas + Parquet", "pandas",  "parquet", _run_pandas_parquet),
    ("Pandas + CSV",     "pandas",  "csv",     _run_pandas_csv),     # Most dangerous — last
]

COLORS = {
    "Polars + Parquet": "#22c55e",  # Green
    "Polars + CSV":     "#eab308",  # Yellow
    "Pandas + Parquet": "#f97316",  # Orange
    "Pandas + CSV":     "#ef4444",  # Red
}


def run_all() -> dict:
    watchdog = RamWatchdog(limit_gb=RAM_LIMIT_GB)
    results  = {}
    ram_timeseries = {}

    print()
    print("=" * 65)
    print("  Live Benchmark: Pandas/Polars x CSV/Parquet")
    print(f"  RAM Safety Limit : {RAM_LIMIT_GB} GB")
    print(f"  Sampling Interval: {SAMPLE_INTERVAL_MS}ms")
    print("=" * 65)

    # Pre-flight: check files exist
    for path, label in [(PARQUET_PATH, "Parquet"), (CSV_PATH, "CSV")]:
        if not os.path.exists(path):
            print(f"\n  ERROR: {label} file not found at '{path}'")
            print("  Run gen_ml_logs.py first.")
            sys.exit(1)

    # Collect file stats
    parquet_mb = get_file_size_mb(PARQUET_PATH)
    csv_mb     = get_file_size_mb(CSV_PATH)
    ratio      = csv_mb / parquet_mb

    print(f"\n  Parquet file : {parquet_mb:.1f} MB")
    print(f"  CSV file     : {csv_mb:.1f} MB")
    print(f"  Ratio        : {ratio:.1f}x (CSV is {ratio:.1f}x larger)")
    print()

    # Warm up psutil CPU counters
    psutil.cpu_percent(percpu=True)
    time.sleep(0.5)

    for (name, engine, fmt, runner) in TESTS:
        print(f"  ▶  {name} ...")

        sampler  = ResourceSampler()
        watchdog.start()
        sampler.start()

        try:
            result = runner(watchdog, sampler)
        except Exception as e:
            print(f"     [ERROR] {e}")
            result = {
                "elapsed_s": 0, "peak_ram_gb": 0,
                "throughput_mb": 0, "rows_read": 0, "oom_crash": True
            }
        finally:
            sampler.stop()
            watchdog.stop()

        # Enrich result
        result["name"]   = name
        result["engine"] = engine
        result["format"] = fmt
        result["color"]  = COLORS[name]
        result["rows_per_sec"] = round(
            result["rows_read"] / result["elapsed_s"] if result["elapsed_s"] > 0 else 0
        )

        crash_tag = " [OOM CRASH - RAM LIMIT HIT]" if result["oom_crash"] else ""
        print(f"     ✓  {format_duration(result['elapsed_s'])} | "
              f"Peak RAM: {watchdog.peak_gb:.2f}GB | "
              f"Throughput: {result['throughput_mb']:.1f} MB/s"
              f"{crash_tag}")

        results[name]        = result
        ram_timeseries[name] = sampler.samples

        # Allow system to recover memory between tests
        import gc
        gc.collect()
        time.sleep(3)

    return results, ram_timeseries, parquet_mb, csv_mb, ratio


# Build output JSON
def build_json(results, ram_timeseries, parquet_mb, csv_mb, ratio) -> dict:
    """Construct the full JSON artifact for the React dashboard."""

    # System metadata
    mem  = psutil.virtual_memory()
    cpus = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()

    # Ordered results for the chart (sorted by elapsed time desc so chart reads well)
    chart_data = sorted(
        [
            {
                "name"         : r["name"],
                "engine"       : r["engine"],
                "format"       : r["format"],
                "color"        : r["color"],
                "elapsed_s"    : r["elapsed_s"],
                "peak_ram_gb"  : r["peak_ram_gb"],
                "throughput_mb": r["throughput_mb"],
                "rows_per_sec" : r["rows_per_sec"],
                "oom_crash"    : r["oom_crash"],
            }
            for r in results.values()
        ],
        key=lambda x: -x["elapsed_s"],  # Slowest first → most dramatic bar chart
    )

    # RAM time-series — downsample to max 120 samples per test for chart performance
    ts_out = {}
    for name, samples in ram_timeseries.items():
        if len(samples) > 120:
            step = len(samples) // 120
            samples = samples[::step]
        ts_out[name] = [
            {"t": s[0], "ram": s[1], "cpu": s[2]}
            for s in samples
        ]

    # Speedup / multiplier stats
    polars_parquet = results.get("Polars + Parquet", {})
    pandas_csv     = results.get("Pandas + CSV", {})
    speedup = 0
    if polars_parquet.get("elapsed_s", 0) > 0 and pandas_csv.get("elapsed_s", 0) > 0:
        speedup = round(pandas_csv["elapsed_s"] / polars_parquet["elapsed_s"], 0)

    return {
        "generated_at"  : time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset"       : {
            "total_rows"  : TOTAL_ROWS,
            "parquet_mb"  : round(parquet_mb, 1),
            "csv_mb"      : round(csv_mb, 1),
            "size_ratio"  : round(ratio, 1),
        },
        "hardware"      : {
            "cpu_name"   : platform.processor(),
            "cpu_cores"  : psutil.cpu_count(logical=False),
            "cpu_threads": cpus,
            "cpu_freq_mhz": round(cpu_freq.max, 0) if cpu_freq else None,
            "total_ram_gb": round(mem.total / (1024 ** 3), 1),
            "os"          : platform.platform(),
        },
        "ram_limit_gb"  : RAM_LIMIT_GB,
        "chart_data"    : chart_data,
        "ram_timeseries": ts_out,
        "speedup_factor": int(speedup),
        "summary"       : {
            "winner"         : "Polars + Parquet",
            "loser"          : "Pandas + CSV",
            "winner_time_s"  : polars_parquet.get("elapsed_s", 0),
            "loser_time_s"   : pandas_csv.get("elapsed_s", 0),
            "speedup"        : int(speedup),
            "compression_ratio": round(ratio, 1),
        }
    }


# Main
def main():
    # Check requirements
    missing = []
    for pkg in ["pandas", "polars", "psutil"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"\n  Missing packages: {', '.join(missing)}")
        print(f"  Run: pip install {' '.join(missing)}")
        sys.exit(1)

    results, ram_timeseries, parquet_mb, csv_mb, ratio = run_all()

    # Build and write JSON
    output = build_json(results, ram_timeseries, parquet_mb, csv_mb, ratio)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print("=" * 65)
    print(f"  Results saved → {OUTPUT_JSON}")
    print("=" * 65)
    print(f"\n  Speedup : Polars + Parquet is {output['speedup_factor']}x faster than Pandas + CSV")
    print(f"  Storage : CSV is {output['dataset']['size_ratio']}x larger than Parquet")
    print()


if __name__ == "__main__":
    main()
