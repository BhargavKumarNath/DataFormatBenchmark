import { GlassCard } from '../ui/GlassCard';
import { benchmarkData } from '../../data/benchmarkStats';

export const HardwareMetrics = () => {
  const python = benchmarkData.python;
  const numpy = benchmarkData.numpy;
  const scale = '100M';

  const metrics = [
    {
      title: "Heap Memory Layout",
      subtitle: "Footprint at 100M Rows",
      pyType: python.memory.type,
      pyVal: python.memory[scale],
      npType: numpy.memory.type,
      npVal: numpy.memory[scale]
    },
    {
      title: "CPU Cache Efficiency",
      subtitle: "L1/L2 Pre-fetching Hit Rate",
      pyType: python.cache.description,
      pyVal: `${python.cache.l1l2HitRate}%`,
      npType: numpy.cache.description,
      npVal: `${numpy.cache.l1l2HitRate}%`
    },
    {
      title: "Execution Pipeline",
      subtitle: "Hardware Instruction Processing",
      pyType: python.simd.type,
      pyVal: python.simd.opsPerSecond,
      npType: numpy.simd.type,
      npVal: numpy.simd.opsPerSecond
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {metrics.map((metric, idx) => (
        <GlassCard key={idx} title={metric.title} className="min-h-[250px]">
          <div className="text-zinc-500 text-xs uppercase tracking-widest mb-6 border-b border-white/5 pb-2 text-center">
            {metric.subtitle}
          </div>
          
          <div className="flex flex-col gap-6">
            {/* Python Row */}
            <div className="flex justify-between items-center bg-red-500/5 p-4 rounded-xl border border-red-500/10">
              <div className="flex flex-col text-left">
                <span className="text-red-400/50 text-[10px] font-bold uppercase tracking-wider mb-1">Pure Python</span>
                <span className="text-red-400 text-sm font-semibold">{metric.pyType}</span>
              </div>
              <span className="text-2xl font-mono font-bold text-red-500 text-right">{metric.pyVal}</span>
            </div>

            {/* NumPy Row */}
            <div className="flex justify-between items-center bg-green-500/5 p-4 rounded-xl border border-green-500/10 shadow-[0_0_15px_rgba(34,197,94,0.05)]">
              <div className="flex flex-col text-left">
                <span className="text-green-400/50 text-[10px] font-bold uppercase tracking-wider mb-1">NumPy Vectorized</span>
                <span className="text-green-400 text-sm font-semibold">{metric.npType}</span>
              </div>
              <span className="text-2xl font-mono font-bold text-green-400 text-right drop-shadow-[0_0_8px_rgba(74,222,128,0.3)]">{metric.npVal}</span>
            </div>
          </div>
        </GlassCard>
      ))}
    </div>
  );
};
