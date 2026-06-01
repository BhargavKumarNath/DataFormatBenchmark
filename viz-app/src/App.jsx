import { StorageCards } from './components/visualizers/StorageCards';
import { LoadTimeChart } from './components/visualizers/LoadTimeChart';
import { RamCrashChart } from './components/visualizers/RamCrashChart';
import { CorePipeline } from './components/visualizers/CorePipeline';
import { PredicatePushdown } from './components/visualizers/PredicatePushdown';
import liveResults from './data/live_results.json';

function App() {
  const { hardware, dataset, summary } = liveResults;

  return (
    <div className="min-h-screen p-6 md:p-12 text-white max-w-[1000px] mx-auto flex flex-col font-sans bg-[#09090b]">
      <header className="mb-10 flex flex-col items-center text-center">
        <h1 className="text-4xl md:text-5xl font-extrabold mb-4 tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-zinc-100 to-zinc-500">
          Parquet + Polars vs CSV + Pandas
        </h1>
        <p className="text-zinc-400 font-medium tracking-wide text-lg max-w-2xl mb-6">
          Why loading large datasets in Pandas crashes your laptop, and how Polars fixes it.
        </p>

        {/* Live hardware badge */}
        <div className="flex flex-wrap gap-3 justify-center">
          {[
            { label: 'CPU', value: `${hardware.cpu_cores}c/${hardware.cpu_threads}t` },
            { label: 'RAM', value: `${hardware.total_ram_gb.toFixed(0)} GB` },
            { label: 'Dataset', value: `${(dataset.total_rows / 1_000_000).toFixed(0)}M Rows` },
            { label: 'Speedup', value: `${summary.speedup}x Faster` },
            { label: 'Compression', value: `${summary.compression_ratio}x Smaller` },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center gap-2 bg-white/5 border border-white/10 px-4 py-1.5 rounded-full">
              <span className="text-zinc-500 text-[10px] uppercase tracking-widest font-mono">{label}</span>
              <span className="text-white text-xs font-bold font-mono">{value}</span>
            </div>
          ))}
        </div>
      </header>

      <main className="flex-1 w-full flex flex-col gap-8">
        {/* 1. The speed proof */}
        <LoadTimeChart />

        {/* 2. Why: file format */}
        <StorageCards />

        {/* 3. Why: RAM behaviour */}
        <RamCrashChart />

        {/* 4. Why: CPU utilisation */}
        <CorePipeline />

        {/* 5. Advanced: Predicate Pushdown */}
        <PredicatePushdown />
      </main>

      <footer className="mt-12 text-center text-zinc-600 text-xs font-mono uppercase tracking-widest pb-12 space-y-1">
        <p>{hardware.cpu_name} · {hardware.total_ram_gb.toFixed(0)}GB RAM · {hardware.os.split('-').slice(0, 2).join(' ')}</p>
        <p>Dataset: {(dataset.total_rows / 1_000_000).toFixed(0)}M rows — Parquet {dataset.parquet_mb.toFixed(0)}MB · CSV {(dataset.csv_mb / 1024).toFixed(1)}GB · Benchmark {liveResults.generated_at.slice(0, 10)}</p>
      </footer>
    </div>
  );
}

export default App;
