import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { GlassCard } from '../ui/GlassCard';

export const PerformanceChart = () => {
  // Aggregate data for 1 Billion transactions
  const chartData = [
    {
      name: 'Pure Python',
      time: 640000, // 640 seconds (Over 10 minutes)
      color: '#ef4444' // Red
    },
    {
      name: 'NumPy Vectorized',
      time: 7800, // 7.8 seconds
      color: '#22c55e' // Green
    }
  ];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-black/90 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl">
          <p className="text-zinc-400 text-[10px] uppercase font-bold tracking-widest mb-1">Total Compute Time</p>
          <p className={`text-2xl font-mono font-bold ${data.name === 'Pure Python' ? 'text-red-500' : 'text-green-400'}`}>
            {(data.time / 1000).toFixed(1)}s
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard className="w-full relative overflow-hidden border-0 bg-gradient-to-br from-black/80 to-zinc-900/50">
      <div className="flex flex-col md:flex-row items-center justify-between p-4 md:p-8">
        
        <div className="w-full md:w-1/2 flex flex-col justify-center pr-8 z-10 mb-8 md:mb-0">
          <span className="text-zinc-500 font-mono tracking-widest text-xs uppercase mb-4 border border-white/10 w-max px-3 py-1 rounded-full bg-black/50 bg-red-500/10 text-red-400 border-red-500/30">Extreme Scale Test</span>
          <h2 className="text-4xl md:text-5xl font-extrabold text-white leading-tight tracking-tighter mb-4">
            Processing <span className="text-zinc-400">1 BILLION</span> Transactions
          </h2>
          <p className="text-zinc-400 text-sm md:text-base leading-relaxed mb-8 max-w-md">
            When scaling to 1,000,000,000 records on a 16GB RAM laptop, the hardware constraints become fatal. 
            <strong className="text-white ml-1">Python takes over 10 minutes (and crashes). NumPy finishes in 7 seconds.</strong>
          </p>
          <div className="flex gap-4">
            <div className="flex flex-col">
              <span className="text-red-500 font-mono font-bold text-3xl">640.0s</span>
              <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-1">Python Loops</span>
            </div>
            <div className="w-px bg-white/10 mx-2" />
            <div className="flex flex-col">
              <span className="text-green-400 font-mono font-bold text-3xl">7.8s</span>
              <span className="text-zinc-500 text-[10px] uppercase tracking-widest mt-1">NumPy Vectorized</span>
            </div>
          </div>
        </div>

        <div className="w-full md:w-1/2 h-[300px] relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
            >
              <XAxis type="number" hide />
              <YAxis 
                type="category" 
                dataKey="name" 
                stroke="#71717a" 
                tick={{ fill: '#a1a1aa', fontSize: 12, fontWeight: 600 }}
                tickLine={false}
                axisLine={false}
                width={120}
              />
              <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} content={<CustomTooltip />} />
              <Bar dataKey="time" radius={[0, 4, 4, 0]} barSize={40}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>
      
      {/* Background ambient lighting */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-green-500/10 blur-[100px] pointer-events-none rounded-full" />
    </GlassCard>
  );
};
