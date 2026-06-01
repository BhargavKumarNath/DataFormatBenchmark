import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { GlassCard } from '../ui/GlassCard';
import liveResults from '../../data/live_results.json';

export const RamCrashChart = () => {
  const { ram_timeseries, ram_limit_gb, hardware } = liveResults;

  // Build unified time-series aligned at t=0 for the two most dramatic tests
  const pandasCsvSeries   = ram_timeseries['Pandas + CSV']   || [];
  const polarsParquetSeries = ram_timeseries['Polars + Parquet'] || [];

  // Merge all timestamps and interpolate
  const allTimes = Array.from(
    new Set([...pandasCsvSeries.map(s => s.t), ...polarsParquetSeries.map(s => s.t)])
  ).sort((a, b) => a - b);

  const mergedData = allTimes.map(t => {
    const findNearest = (series, time) => {
      const exact = series.find(s => s.t === time);
      if (exact) return exact.ram;
      const before = [...series].reverse().find(s => s.t <= time);
      return before ? before.ram : null;
    };
    return {
      t: parseFloat(t.toFixed(2)),
      pandasCsv: findNearest(pandasCsvSeries, t),
      polarsParquet: findNearest(polarsParquetSeries, t),
    };
  });

  const pandasCsvPeak   = Math.max(...pandasCsvSeries.map(s => s.ram));
  const polarsPeak      = Math.max(...polarsParquetSeries.map(s => s.ram));
  const yDomain         = [Math.min(pandasCsvSeries[0]?.ram ?? 0, polarsParquetSeries[0]?.ram ?? 0) - 1, Math.max(pandasCsvPeak, polarsPeak, ram_limit_gb) + 0.5];

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/90 backdrop-blur-md border border-white/10 p-3 rounded-xl shadow-2xl min-w-[170px]">
          <p className="text-zinc-500 text-[10px] font-mono mb-2">t = {label}s</p>
          {payload.map((entry, i) => entry.value && (
            <div key={i} className="flex justify-between items-center mb-1 gap-3">
              <span className="text-[10px] uppercase font-bold" style={{ color: entry.color }}>{entry.name}</span>
              <span className="font-mono font-bold text-sm" style={{ color: entry.color }}>{entry.value.toFixed(2)} GB</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard title="2. RAM Under Fire (Eager vs Lazy Loading)" className="w-full">
      <div className="flex flex-col md:flex-row gap-8 mt-4">

        {/* Context cards */}
        <div className="w-full md:w-1/3 flex flex-col justify-center gap-5">
          <div className="border-l-2 border-red-500 pl-4">
            <h4 className="text-red-400 font-bold uppercase tracking-widest text-sm mb-1">Pandas — Eager</h4>
            <p className="text-zinc-400 text-xs leading-relaxed">
              Loads the entire file into RAM immediately. RAM spikes steadily until the hardware limit triggers an Out-of-Memory kill.
            </p>
            <div className="mt-2 flex gap-3">
              <span className="text-red-500 font-mono font-bold text-sm">{pandasCsvPeak.toFixed(1)} GB</span>
              <span className="text-zinc-600 text-[10px] uppercase self-end tracking-widest">Peak RAM</span>
            </div>
          </div>

          <div className="border-l-2 border-green-500 pl-4">
            <h4 className="text-green-400 font-bold uppercase tracking-widest text-sm mb-1">Polars — Lazy</h4>
            <p className="text-zinc-400 text-xs leading-relaxed">
              Memory-maps the file. Treats the SSD as RAM. No eager allocation — finishes in seconds without touching the limit.
            </p>
            <div className="mt-2 flex gap-3">
              <span className="text-green-400 font-mono font-bold text-sm">{polarsPeak.toFixed(1)} GB</span>
              <span className="text-zinc-600 text-[10px] uppercase self-end tracking-widest">Peak RAM</span>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 px-3 py-2 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
            <span className="text-red-400 text-[10px] font-mono uppercase tracking-widest">
              {hardware.total_ram_gb.toFixed(1)} GB Hardware Limit
            </span>
          </div>
        </div>

        {/* Line chart */}
        <div className="w-full md:w-2/3 h-[260px] relative">
          <div className="absolute top-0 right-0 bg-red-500 text-white text-[9px] font-bold font-mono px-2 py-1 rounded animate-pulse z-20 shadow-[0_0_12px_rgba(239,68,68,0.8)]">
            [OOM — RAM LIMIT HIT]
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mergedData} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="t"
                stroke="#71717a"
                tick={{ fill: '#71717a', fontSize: 10 }}
                label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -5, fill: '#52525b', fontSize: 10 }}
              />
              <YAxis
                stroke="#71717a"
                tick={{ fill: '#71717a', fontSize: 10 }}
                domain={[Math.floor(yDomain[0]), Math.ceil(yDomain[1])]}
                unit=" GB"
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={ram_limit_gb}
                stroke="#ef4444"
                strokeDasharray="4 3"
                strokeWidth={2}
                label={{ position: 'insideTopLeft', value: `${ram_limit_gb}GB LIMIT`, fill: '#ef4444', fontSize: 9, fontWeight: 'bold', fontFamily: 'monospace' }}
              />
              <Line
                type="monotone"
                dataKey="pandasCsv"
                name="Pandas + CSV"
                stroke="#ef4444"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5, fill: '#ef4444', strokeWidth: 0 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="polarsParquet"
                name="Polars + Parquet"
                stroke="#22c55e"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5, fill: '#22c55e', strokeWidth: 0 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

      </div>
    </GlassCard>
  );
};
