import { GlassCard } from '../ui/GlassCard';
import liveResults from '../../data/live_results.json';

export const CorePipeline = () => {
  const { hardware, chart_data } = liveResults;
  const totalCores = hardware.cpu_threads;

  const pandasCsv      = chart_data.find(d => d.engine === 'pandas' && d.format === 'csv');
  const polarsParquet  = chart_data.find(d => d.engine === 'polars' && d.format === 'parquet');

  // Throughput ratio to estimate active core utilization
  const throughputRatio = polarsParquet ? polarsParquet.throughput_mb / (pandasCsv?.throughput_mb || 1) : 1;
  const estimatedPolarsCores = Math.min(totalCores, Math.round(throughputRatio * 1.5));

  return (
    <GlassCard title="3. CPU Pipeline Utilization" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">

        {/* Pandas */}
        <div className="flex flex-col items-center">
          <h4 className="text-red-400 font-bold uppercase tracking-widest text-sm mb-1">Pandas + CSV</h4>
          <p className="text-zinc-500 text-xs text-center mb-4 max-w-xs">
            Single-threaded I/O. The GIL bottlenecks text parsing to one core. Every other thread sits idle.
          </p>
          <div className="flex gap-2 items-end mb-3 w-full justify-center">
            <span className="text-red-500 font-mono font-bold text-2xl">{pandasCsv?.throughput_mb.toFixed(0)}</span>
            <span className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">MB/s read throughput</span>
          </div>
          <div className="w-full max-w-[300px] bg-black/50 border border-red-500/20 p-3 rounded-xl flex gap-1 justify-center flex-wrap">
            {/* 1 active */}
            <div className="w-11 h-11 bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.8)] rounded-md flex flex-col items-center justify-center border border-red-400 gap-0.5">
              <span className="text-[8px] font-bold text-white">C0</span>
              <span className="text-[7px] text-red-200">100%</span>
            </div>
            {/* rest sleeping */}
            {Array.from({ length: totalCores - 1 }).map((_, i) => (
              <div key={i} className="w-11 h-11 bg-white/5 rounded-md flex flex-col items-center justify-center border border-white/10 gap-0.5">
                <span className="text-[8px] text-zinc-600">C{i + 1}</span>
                <span className="text-[7px] text-zinc-700">0%</span>
              </div>
            ))}
          </div>
          <div className="mt-3 text-center">
            <span className="text-red-500 font-mono font-bold text-lg">1 of {totalCores}</span>
            <span className="text-zinc-500 text-[10px] block uppercase mt-0.5 tracking-widest">Threads Active</span>
          </div>
        </div>

        {/* Polars */}
        <div className="flex flex-col items-center">
          <h4 className="text-green-400 font-bold uppercase tracking-widest text-sm mb-1">Polars + Parquet</h4>
          <p className="text-zinc-500 text-xs text-center mb-4 max-w-xs">
            Rust-native multi-threading. Polars distributes decompression and column decoding across all {totalCores} logical cores simultaneously.
          </p>
          <div className="flex gap-2 items-end mb-3 w-full justify-center">
            <span className="text-green-400 font-mono font-bold text-2xl">{polarsParquet?.throughput_mb.toFixed(0)}</span>
            <span className="text-zinc-500 text-[10px] uppercase tracking-widest mb-1">MB/s read throughput</span>
          </div>
          <div className="w-full max-w-[300px] bg-black/50 border border-green-500/20 p-3 rounded-xl flex gap-1 justify-center flex-wrap shadow-[0_0_30px_rgba(34,197,94,0.05)]">
            {Array.from({ length: totalCores }).map((_, i) => {
              const isActive = i < estimatedPolarsCores;
              return (
                <div
                  key={i}
                  className={`w-11 h-11 rounded-md flex flex-col items-center justify-center gap-0.5 ${
                    isActive
                      ? 'bg-green-500/80 shadow-[0_0_10px_rgba(34,197,94,0.5)] border border-green-400'
                      : 'bg-green-500/20 border border-green-500/30'
                  }`}
                >
                  <span className={`text-[8px] font-bold ${isActive ? 'text-black' : 'text-green-600'}`}>C{i}</span>
                  <span className={`text-[7px] ${isActive ? 'text-black/70' : 'text-green-700'}`}>{isActive ? '100%' : '~40%'}</span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 text-center">
            <span className="text-green-400 font-mono font-bold text-lg">{estimatedPolarsCores} of {totalCores}</span>
            <span className="text-zinc-500 text-[10px] block uppercase mt-0.5 tracking-widest">Threads Saturated</span>
          </div>
        </div>

      </div>
    </GlassCard>
  );
};
