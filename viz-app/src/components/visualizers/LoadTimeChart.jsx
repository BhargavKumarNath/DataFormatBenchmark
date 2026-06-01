import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts';
import { GlassCard } from '../ui/GlassCard';
import liveResults from '../../data/live_results.json';

export const LoadTimeChart = () => {
  const { chart_data, dataset, hardware, speedup_factor } = liveResults;

  // chart_data is already sorted slowest→fastest
  const chartData = chart_data.map(d => ({
    name: d.name,
    time: d.elapsed_s,
    color: d.color,
    oom: d.oom_crash,
    label: d.oom_crash
      ? `${d.elapsed_s.toFixed(1)}s ⚠ OOM`
      : `${d.elapsed_s.toFixed(2)}s`,
  }));

  const winner = chart_data.find(d => d.engine === 'polars' && d.format === 'parquet');
  const loser  = chart_data.find(d => d.engine === 'pandas' && d.format === 'csv');

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-black/90 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl min-w-[200px]">
          <p className="text-zinc-400 text-[10px] uppercase font-bold tracking-widest mb-1">{d.name}</p>
          <p className="font-mono font-bold text-2xl" style={{ color: d.color }}>{d.label}</p>
          {d.oom && <p className="text-red-400 text-[10px] font-mono mt-1">RAM limit hit — benchmark stopped</p>}
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard className="w-full relative overflow-hidden border-0 bg-gradient-to-br from-black/80 to-zinc-900/50">
      <div className="flex flex-col md:flex-row items-center justify-between p-4 md:p-8">

        {/* Left: headline */}
        <div className="w-full md:w-1/2 flex flex-col justify-center pr-8 z-10 mb-8 md:mb-0">
          <span className="text-red-400 font-mono tracking-widest text-xs uppercase mb-4 border border-red-500/30 w-max px-3 py-1 rounded-full bg-red-500/10">
            Live Benchmark · {hardware.cpu_name.split(',')[0]}
          </span>
          <h2 className="text-4xl md:text-5xl font-extrabold text-white leading-tight tracking-tighter mb-4">
            Loading <span className="text-zinc-400">{(dataset.total_rows / 1_000_000).toFixed(0)}M rows</span>
          </h2>
          <p className="text-zinc-400 text-sm md:text-base leading-relaxed mb-8 max-w-md">
            Same data, same machine, same query. The format + engine choice is the only variable.
            <strong className="text-white ml-1">Polars + Parquet is {speedup_factor}x faster.</strong>
          </p>
          <div className="flex gap-6">
            <div className="flex flex-col">
              <span className="text-red-500 font-mono font-bold text-2xl md:text-3xl">
                {loser?.elapsed_s.toFixed(1)}s
              </span>
              <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-1">Pandas + CSV</span>
            </div>
            <div className="w-px bg-white/10 mx-2" />
            <div className="flex flex-col">
              <span className="text-green-400 font-mono font-bold text-2xl md:text-3xl">
                {winner?.elapsed_s.toFixed(2)}s
              </span>
              <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-1">Polars + Parquet</span>
            </div>
          </div>
        </div>

        {/* Right: bar chart */}
        <div className="w-full md:w-1/2 h-[280px] relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 10, right: 80, left: 110, bottom: 10 }}
            >
              <XAxis type="number" hide domain={[0, loser?.elapsed_s * 1.1]} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#71717a"
                tick={{ fill: '#a1a1aa', fontSize: 11, fontWeight: 600 }}
                tickLine={false}
                axisLine={false}
                width={110}
              />
              <Tooltip cursor={{ fill: 'rgba(255,255,255,0.04)' }} content={<CustomTooltip />} />
              <Bar dataKey="time" radius={[0, 4, 4, 0]} barSize={34}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
                <LabelList
                  dataKey="label"
                  position="right"
                  style={{ fill: '#a1a1aa', fontSize: 11, fontFamily: 'monospace', fontWeight: 600 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>
      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-green-500/8 blur-[100px] pointer-events-none rounded-full" />
    </GlassCard>
  );
};
