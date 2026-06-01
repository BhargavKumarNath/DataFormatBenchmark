import { GlassCard } from '../ui/GlassCard';

export const DataStream = () => {
  return (
    <GlassCard title="3. The Data Stream (Cache Fetching & SIMD Vectorization)" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mt-4">
        
        {/* Python View */}
        <div className="flex flex-col items-center">
          <h4 className="text-red-400 font-bold uppercase tracking-widest text-sm mb-2">Sequential Fetching</h4>
          <p className="text-zinc-500 text-xs text-center mb-6 max-w-xs">Python's GIL restricts the CPU to pulling one piece of data at a time. Cache misses constantly stall the CPU.</p>
          
          <div className="w-full max-w-[300px] h-32 relative flex items-center justify-center border border-red-500/20 rounded-xl bg-black/50 overflow-hidden">
            <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_20%,rgba(239,68,68,0.1)_50%,transparent_80%)]" />
            {/* Sequential Blocks */}
            <div className="flex gap-4 items-center">
              <div className="w-4 h-4 bg-red-500/20 rounded-sm" />
              <div className="w-4 h-4 bg-red-500/40 rounded-sm" />
              <div className="w-4 h-4 bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)] rounded-sm" />
              <div className="w-4 h-4 bg-red-500/40 rounded-sm" />
            </div>
            {/* Label */}
            <div className="absolute bottom-2 right-4 text-[10px] text-red-500/50 uppercase font-mono tracking-widest border border-red-500/20 px-2 py-1 rounded">1-by-1 Processing</div>
          </div>
          
          <div className="mt-4 flex gap-4 text-center">
            <div>
              <span className="text-red-500 font-mono font-bold text-lg block">12%</span>
              <span className="text-zinc-600 text-[10px] uppercase">Cache Hit Rate</span>
            </div>
            <div>
              <span className="text-red-500 font-mono font-bold text-lg block">15M</span>
              <span className="text-zinc-600 text-[10px] uppercase">Ops/Second</span>
            </div>
          </div>
        </div>

        {/* NumPy View */}
        <div className="flex flex-col items-center">
          <h4 className="text-green-400 font-bold uppercase tracking-widest text-sm mb-2">SIMD Parallel Pipeline</h4>
          <p className="text-zinc-500 text-xs text-center mb-6 max-w-xs">NumPy uses Single Instruction, Multiple Data (SIMD) to flood the CPU cache and process chunks simultaneously.</p>
          
          <div className="w-full max-w-[300px] h-32 relative flex items-center justify-center border border-green-500/20 rounded-xl bg-black/50 overflow-hidden">
            <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent_20%,rgba(34,197,94,0.1)_50%,transparent_80%)]" />
            {/* Parallel Blocks */}
            <div className="flex flex-col gap-1 w-full px-8">
              {Array.from({ length: 4 }).map((_, colIndex) => (
                <div key={colIndex} className="flex gap-1 justify-center w-full">
                  {Array.from({ length: 8 }).map((_, rowIndex) => {
                    let opacity = "bg-green-500/20";
                    if (colIndex === 2) opacity = "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]"; // The active chunk
                    if (colIndex === 1 || colIndex === 3) opacity = "bg-green-500/60";
                    
                    return <div key={`${colIndex}-${rowIndex}`} className={`h-2 flex-1 rounded-sm ${opacity}`} />
                  })}
                </div>
              ))}
            </div>
            {/* Label */}
            <div className="absolute bottom-2 right-4 text-[10px] text-green-400/50 uppercase font-mono tracking-widest border border-green-500/20 px-2 py-1 rounded">256-bit Vector Streams</div>
          </div>
          
          <div className="mt-4 flex gap-4 text-center">
            <div>
              <span className="text-green-400 font-mono font-bold text-lg block">98%</span>
              <span className="text-zinc-600 text-[10px] uppercase">Cache Hit Rate</span>
            </div>
            <div>
              <span className="text-green-400 font-mono font-bold text-lg block">1.8B</span>
              <span className="text-zinc-600 text-[10px] uppercase">Ops/Second</span>
            </div>
          </div>
        </div>

      </div>
    </GlassCard>
  );
};
