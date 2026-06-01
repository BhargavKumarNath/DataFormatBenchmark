import { GlassCard } from '../ui/GlassCard';

export const AssemblyCode = () => {
  return (
    <GlassCard title="4. The Operation Cost (Interpreter vs Silicon)" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">
        
        {/* Python Playcard */}
        <div className="bg-gradient-to-b from-red-500/10 to-transparent border border-red-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-red-500/10 rounded-full blur-2xl" />
          
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-red-400 font-bold uppercase tracking-widest text-lg">Python Addition</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Bytecode Interpreter</span>
            </div>
            <div className="bg-red-500/20 text-red-500 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-red-500/30">
              ~20 Ops
            </div>
          </div>

          {/* Visual Grid */}
          <div className="mb-4 flex flex-col gap-2">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Instructions Fired</span>
            <div className="flex flex-wrap gap-1">
              {Array.from({ length: 20 }).map((_, i) => (
                <div key={i} className={`w-3 h-3 rounded-sm ${i === 19 ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]' : 'bg-red-500/30'}`} />
              ))}
            </div>
          </div>
          
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            Adding two numbers requires 19 overhead operations (checking variable types, allocating memory, updating reference counts) before the 1 actual math operation occurs.
          </p>
        </div>

        {/* NumPy Playcard */}
        <div className="bg-gradient-to-b from-green-500/10 to-transparent border border-green-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden shadow-[0_0_30px_rgba(34,197,94,0.05)]">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-green-500/10 rounded-full blur-2xl" />
          
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-green-400 font-bold uppercase tracking-widest text-lg">NumPy Vector Add</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Hardware Silicon</span>
            </div>
            <div className="bg-green-500/20 text-green-400 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-green-500/30 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]">
              1 Op
            </div>
          </div>

          {/* Visual Grid */}
          <div className="mb-4 flex flex-col gap-2">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest">Instructions Fired</span>
            <div className="flex flex-wrap gap-1">
              <div className="w-3 h-3 rounded-sm bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.8)]" />
              {Array.from({ length: 19 }).map((_, i) => (
                <div key={i} className="w-3 h-3 rounded-sm bg-white/5" />
              ))}
            </div>
          </div>
          
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            Bypasses Python completely. It compiles down to a single instruction executed directly on the CPU's logic gates. Zero overhead.
          </p>
        </div>

      </div>
    </GlassCard>
  );
};
