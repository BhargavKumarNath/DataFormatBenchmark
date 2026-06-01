# DataFormatBenchmark

This repository contains the complete code to replicate the "Pandas vs Polars" benchmark run on a local machine. It includes highly optimized data generation scripts to create datasets spanning hundreds of millions of rows, the benchmarking logic, and a React dashboard to visualize the hardware telemetry.

## Quick Start

You can get the interactive dashboard running locally with just a few commands. 

```bash
# Clone the repository
git clone https://github.com/BhargavKumarNath/DataFormatBenchmark.git
cd DataFormatBenchmark

# Install frontend dependencies and start the React dashboard
npm install
npm run dev
```
Open `http://localhost:5173/` in your browser. The dashboard comes pre-loaded with sample benchmark data so you can view it immediately.

## Generate the Data (100M+ Rows)

If you want to run the benchmarks yourself, you first need to generate the datasets. We have provided 5 distinct, highly optimized data generation scripts. Each script uses PyArrow to stream data directly to disk without blowing up your RAM.

First, set up your Python environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

Run any of the following scripts to generate large-scale datasets (saved to the `data/` folder in both CSV and Parquet formats):

```bash
# 1. ML Training Logs (25M rows)
python scripts/gen_ml_logs.py

# 2. E-Commerce Transactions (100M rows)
python scripts/gen_ecommerce.py

# 3. IoT Sensor Telemetry (100M rows)
python scripts/gen_iot_sensors.py

# 4. Financial Market Tick Data (200M rows)
python scripts/gen_financial_ticks.py

# 5. Clickstream Analytics (100M rows)
python scripts/gen_clickstream.py
```

## Run the Benchmarks

Once you've generated the `data/ml_logs_25m.csv` and `data/ml_logs_25m.parquet` files, you can run the benchmarking scripts to see how your own hardware handles the load.

```bash
# Benchmark full dataset load times and track RAM usage
python scripts/run_benchmark.py

# Benchmark query times & disk I/O using Predicate Pushdown
python scripts/run_predicate_benchmark.py
```

These scripts will output real-time terminal results and save the telemetry to JSON files in the `viz-app/src/data/` folder. The React dashboard will hot-reload automatically to reflect your machine's actual hardware performance!
