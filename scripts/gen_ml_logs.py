"""
gen_ml_logs.py
--------------
Generates a hyperrealistic ML Training Logs dataset for benchmarking
Pandas/CSV vs Polars/Parquet on large-scale data operations.

Schema (13 columns):
  - 5 Categorical identifiers (framework, optimizer, loss, hardware, hash)
  - 6 Numerical hyperparameters & metrics
  - 1 Temporal (step_timestamp)

Memory Strategy (safe for 16GB RAM laptops):
  - Data is generated in configurable chunks using NumPy (no Pandas).
  - Each chunk is streamed directly to disk via PyArrow ParquetWriter.
  - Peak RAM usage per chunk is approx 80-120MB regardless of total rows.
  - CSV is written using chunked iteration, never loading the full file.

Requirements:
  pip install numpy pyarrow tqdm
"""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pa_csv
import time
import os
import sys
from tqdm import tqdm

# Configuration
TOTAL_ROWS  = 25_000_000          # 25M rows — enough to stress Pandas/CSV
CHUNK_SIZE  = 500_000             # ~100MB RAM peak per chunk
PARQUET_OUT = "data/ml_logs_25m.parquet"
CSV_OUT     = "data/ml_logs_25m.csv"
RANDOM_SEED = 42

# Realistic categorical pools
FRAMEWORKS     = ["PyTorch", "TensorFlow", "JAX", "Scikit-Learn"]
OPTIMIZERS     = ["AdamW", "SGD", "RMSprop", "Adafactor"]
LOSS_FUNCTIONS = ["CrossEntropy", "MSE", "Huber", "FocalLoss"]
HARDWARE       = ["NVIDIA-H100", "NVIDIA-A100", "TPU-v5", "Apple-M3-Max"]
BATCH_SIZES    = [32, 64, 128, 256, 512]

# Realistic probability weights (not perfectly uniform — mirrors real usage)
FRAMEWORK_WEIGHTS  = [0.45, 0.30, 0.15, 0.10]
OPTIMIZER_WEIGHTS  = [0.50, 0.25, 0.15, 0.10]
LOSS_WEIGHTS       = [0.40, 0.25, 0.20, 0.15]
HARDWARE_WEIGHTS   = [0.30, 0.35, 0.20, 0.15]
BATCH_WEIGHTS      = [0.10, 0.20, 0.35, 0.25, 0.10]

# PyArrow schema (enforces dtypes — keeps parquet file tight)
SCHEMA = pa.schema([
    pa.field("model_run_sha256",    pa.dictionary(pa.int16(), pa.utf8())),
    pa.field("framework",           pa.dictionary(pa.int8(),  pa.utf8())),
    pa.field("optimizer_type",      pa.dictionary(pa.int8(),  pa.utf8())),
    pa.field("loss_function",       pa.dictionary(pa.int8(),  pa.utf8())),
    pa.field("hardware_target",     pa.dictionary(pa.int8(),  pa.utf8())),
    pa.field("epoch_number",        pa.int32()),
    pa.field("batch_size",          pa.int32()),
    pa.field("learning_rate",       pa.float32()),
    pa.field("weight_decay",        pa.float32()),
    pa.field("training_loss",       pa.float32()),
    pa.field("validation_accuracy", pa.float32()),
    pa.field("gradient_norm",       pa.float32()),
    pa.field("step_timestamp",      pa.timestamp("ms")),
])

# SHA256-like hash pool (pre-generate so we can dictionary-encode them)
def _make_sha_pool(rng: np.random.Generator, n: int = 10_000) -> list[str]:
    """Generate n realistic-looking short SHA256 hashes."""
    chars = "0123456789abcdef"
    return [
        "".join(rng.choice(list(chars), size=16).tolist())
        for _ in range(n)
    ]

# Core chunk generation — pure NumPy, zero Python loops on rows
def generate_chunk(
    rng: np.random.Generator,
    sha_pool: list[str],
    sha_indices: np.ndarray,
    base_timestamp_ms: int,
    row_offset: int,
    n: int,
) -> pa.RecordBatch:
    """
    Produce one chunk of `n` rows as a PyArrow RecordBatch.
    All heavy lifting is pure NumPy — no Python loops on data rows.
    """

    # Categorical columns (dictionary-encoded for minimal memory)
    fw_idx  = rng.choice(len(FRAMEWORKS),     size=n, p=FRAMEWORK_WEIGHTS).astype(np.int8)
    opt_idx = rng.choice(len(OPTIMIZERS),     size=n, p=OPTIMIZER_WEIGHTS).astype(np.int8)
    los_idx = rng.choice(len(LOSS_FUNCTIONS), size=n, p=LOSS_WEIGHTS).astype(np.int8)
    hw_idx  = rng.choice(len(HARDWARE),       size=n, p=HARDWARE_WEIGHTS).astype(np.int8)

    sha_chunk_idx = sha_indices[row_offset : row_offset + n]

    fw_arr  = pa.DictionaryArray.from_arrays(pa.array(fw_idx,  type=pa.int8()), pa.array(FRAMEWORKS))
    opt_arr = pa.DictionaryArray.from_arrays(pa.array(opt_idx, type=pa.int8()), pa.array(OPTIMIZERS))
    los_arr = pa.DictionaryArray.from_arrays(pa.array(los_idx, type=pa.int8()), pa.array(LOSS_FUNCTIONS))
    hw_arr  = pa.DictionaryArray.from_arrays(pa.array(hw_idx,  type=pa.int8()), pa.array(HARDWARE))
    sha_arr = pa.DictionaryArray.from_arrays(
        pa.array(sha_chunk_idx.astype(np.int16), type=pa.int16()),
        pa.array(sha_pool)
    )

    # Numerical columns
    epoch_number = rng.integers(1, 201, size=n, dtype=np.int32)

    batch_size_vals = np.array(BATCH_SIZES, dtype=np.int32)
    batch_size_idx  = rng.choice(len(BATCH_SIZES), size=n, p=BATCH_WEIGHTS)
    batch_size      = batch_size_vals[batch_size_idx]

    # Learning rate: log-uniform in [1e-5, 1e-2]
    learning_rate = 10 ** rng.uniform(-5, -2, size=n).astype(np.float32)

    # Weight decay: log-uniform in [1e-5, 1e-1]
    weight_decay = 10 ** rng.uniform(-5, -1, size=n).astype(np.float32)

    # Training loss: decays with epoch, with realistic noise
    base_loss = 5.0 / (epoch_number ** 0.5)
    noise     = rng.normal(0, 0.05, size=n).astype(np.float32)
    training_loss = np.clip(base_loss + noise, 0.01, 10.0).astype(np.float32)

    # Validation accuracy: improves with epoch, sigmoid-like
    base_acc = 1.0 / (1.0 + np.exp(-0.05 * (epoch_number - 50)))
    acc_noise = rng.normal(0, 0.01, size=n).astype(np.float32)
    validation_accuracy = np.clip(base_acc + acc_noise, 0.0, 1.0).astype(np.float32)

    # Gradient norm: log-normal, with occasional exploding gradients
    gradient_norm = rng.lognormal(mean=0.5, sigma=1.0, size=n).astype(np.float32)
    # Inject ~1% exploding gradient events for realism
    explosion_mask = rng.random(size=n) < 0.01
    gradient_norm[explosion_mask] *= 50.0
    gradient_norm = np.clip(gradient_norm, 0.001, 1000.0)

    # ---- Temporal column (monotonically increasing, 100ms steps avg) --------
    step_intervals_ms = rng.integers(50, 200, size=n, dtype=np.int64).cumsum()
    timestamps_ms = base_timestamp_ms + step_intervals_ms

    return pa.RecordBatch.from_arrays(
        [
            sha_arr,
            fw_arr,
            opt_arr,
            los_arr,
            hw_arr,
            pa.array(epoch_number,          type=pa.int32()),
            pa.array(batch_size,            type=pa.int32()),
            pa.array(learning_rate,         type=pa.float32()),
            pa.array(weight_decay,          type=pa.float32()),
            pa.array(training_loss,         type=pa.float32()),
            pa.array(validation_accuracy,   type=pa.float32()),
            pa.array(gradient_norm,         type=pa.float32()),
            pa.array(timestamps_ms,         type=pa.timestamp("ms")),
        ],
        schema=SCHEMA,
    ), int(timestamps_ms[-1])

# Write Parquet (primary format, low memory streaming)
def write_parquet(rng, sha_pool, sha_indices):
    os.makedirs(os.path.dirname(PARQUET_OUT), exist_ok=True)

    writer = None
    rows_done = 0
    n_chunks  = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts   = int(time.time() * 1000) - TOTAL_ROWS * 150  # Start in the past

    t0 = time.perf_counter()

    try:
        for _ in tqdm(range(n_chunks), desc="Writing Parquet", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows_done)
            batch, base_ts = generate_chunk(rng, sha_pool, sha_indices, base_ts, rows_done, n)

            if writer is None:
                writer = pq.ParquetWriter(
                    PARQUET_OUT,
                    schema=SCHEMA,
                    compression="snappy",
                    use_dictionary=True,
                    write_statistics=True,
                    data_page_size=1024 * 1024,  # 1MB pages for efficient reads
                )
            writer.write_batch(batch)
            rows_done += n
    finally:
        if writer:
            writer.close()

    elapsed  = time.perf_counter() - t0
    size_mb  = os.path.getsize(PARQUET_OUT) / (1024 ** 2)
    print(f"\n  Parquet done: {rows_done:,} rows | {size_mb:.1f} MB | {elapsed:.1f}s")
    return size_mb

# Write CSV (chunked streaming — never loads full table into RAM)
def write_csv(rng, sha_pool, sha_indices):
    rows_done = 0
    n_chunks  = (TOTAL_ROWS + CHUNK_SIZE - 1) // CHUNK_SIZE
    base_ts   = int(time.time() * 1000) - TOTAL_ROWS * 150

    t0 = time.perf_counter()
    header_written = False

    # IMPORTANT: use "wb" instead of "w"
    with open(CSV_OUT, "wb", buffering=1024 * 1024 * 16) as f:
        for _ in tqdm(range(n_chunks), desc="Writing CSV  ", unit="chunk"):
            n = min(CHUNK_SIZE, TOTAL_ROWS - rows_done)
            batch, base_ts = generate_chunk(
                rng,
                sha_pool,
                sha_indices,
                base_ts,
                rows_done,
                n
            )

            tbl = pa.Table.from_batches([batch])

            pa_csv.write_csv(
                tbl,
                f,
                write_options=pa_csv.WriteOptions(
                    include_header=not header_written
                )
            )

            header_written = True
            rows_done += n

    elapsed = time.perf_counter() - t0
    size_mb = os.path.getsize(CSV_OUT) / (1024 ** 2)

    print(f"  CSV done   : {rows_done:,} rows | {size_mb:.1f} MB | {elapsed:.1f}s")
    return size_mb
# Main
def main():
    print("=" * 60)
    print("  ML Training Logs — Dataset Generator")
    print("=" * 60)
    print(f"  Target rows  : {TOTAL_ROWS:,}")
    print(f"  Chunk size   : {CHUNK_SIZE:,}  (~100MB RAM peak)")
    print(f"  Parquet out  : {PARQUET_OUT}")
    print(f"  CSV out      : {CSV_OUT}")
    print("=" * 60)

    rng      = np.random.default_rng(RANDOM_SEED)
    sha_pool = _make_sha_pool(rng, n=10_000)

    # Pre-assign a sha256 to every row (vectorized, never per-row Python loop)
    sha_indices = rng.integers(0, len(sha_pool), size=TOTAL_ROWS, dtype=np.int16)

    print("\n[1/2] Generating Parquet ...")
    parquet_mb = write_parquet(rng, sha_pool, sha_indices)

    # Re-seed so CSV produces identical logical data
    rng        = np.random.default_rng(RANDOM_SEED)
    sha_pool   = _make_sha_pool(rng, n=10_000)
    sha_indices = rng.integers(0, len(sha_pool), size=TOTAL_ROWS, dtype=np.int16)

    print("\n[2/2] Generating CSV ...")
    csv_mb = write_csv(rng, sha_pool, sha_indices)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Parquet : {parquet_mb:>8.1f} MB")
    print(f"  CSV     : {csv_mb:>8.1f} MB")
    print(f"  Ratio   : {csv_mb / parquet_mb:.1f}x larger (CSV vs Parquet)")
    print("=" * 60)

    # Quick sanity check
    meta = pq.read_metadata(PARQUET_OUT)
    print(f"\n  Parquet row groups : {meta.num_row_groups}")
    print(f"  Schema columns     : {meta.schema.names}")

if __name__ == "__main__":
    main()
