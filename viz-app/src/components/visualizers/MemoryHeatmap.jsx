import { GlassCard } from '../ui/GlassCard';

export const MemoryHeatmap = () => {
  // Generate 100 cells for the heatmap
  const cells = Array.from({ length: 100 }, (_, i) => i);
  
  // Python has scattered memory locations (pseudo-randomly picked)
  const pythonFilled = [2, 7, 14, 18, 25, 33, 41, 48, 55, 62, 74, 81, 88, 95];
  
  // NumPy has contiguous memory locations (exactly 14 blocks packed together)
  const numpyFilled = Array.from({ length: 14 }, (_, i) => i);

  return (
    <GlassCard title="2. Memory Architecture (Why Python struggles to find data)" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mt-4">
        
        {/* Python View */}
        <div className="flex flex-col items-center">
          <h4 className="text-red-400 font-bold uppercase tracking-widest text-sm mb-2">Python Lists</h4>
          <p className="text-zinc-500 text-xs text-center mb-6 max-w-xs">Data is scattered everywhere. The CPU wastes time searching RAM for the next number.</p>
          
          <div className="grid grid-cols-10 gap-1 w-full max-w-[300px]">
            {cells.map((cell) => (
              <div 
                key={`py-${cell}`} 
                className={`w-full aspect-square rounded-sm ${
                  pythonFilled.includes(cell) 
                    ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]' 
                    : 'bg-white/5'
                }`}
              />
            ))}
          </div>
          <div className="mt-4 text-center">
            <span className="text-red-500 font-mono font-bold text-xl">32 GB</span>
            <span className="text-zinc-500 text-xs block uppercase mt-1">Memory Footprint (OOM)</span>
          </div>
        </div>

        {/* NumPy View */}
        <div className="flex flex-col items-center">
          <h4 className="text-green-400 font-bold uppercase tracking-widest text-sm mb-2">NumPy Arrays</h4>
          <p className="text-zinc-500 text-xs text-center mb-6 max-w-xs">Data is perfectly packed in a C-Array. The CPU instantly reads the entire block.</p>
          
          <div className="grid grid-cols-10 gap-1 w-full max-w-[300px]">
            {cells.map((cell) => (
              <div 
                key={`np-${cell}`} 
                className={`w-full aspect-square rounded-sm ${
                  numpyFilled.includes(cell) 
                    ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' 
                    : 'bg-white/5'
                }`}
              />
            ))}
          </div>
          <div className="mt-4 text-center">
            <span className="text-green-400 font-mono font-bold text-xl">8 GB</span>
            <span className="text-zinc-500 text-xs block uppercase mt-1">Memory Footprint</span>
          </div>
        </div>

      </div>
    </GlassCard>
  );
};
