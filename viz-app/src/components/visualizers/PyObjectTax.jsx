import { GlassCard } from '../ui/GlassCard';

export const PyObjectTax = () => {
  return (
    <GlassCard title="1. The Hidden Object Tax (Data Bloat)" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">
        
        {/* Python Playcard */}
        <div className="bg-gradient-to-b from-red-500/10 to-transparent border border-red-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-red-500/10 rounded-full blur-2xl" />
          
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-red-400 font-bold uppercase tracking-widest text-lg">Python Int</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Dynamic Object</span>
            </div>
            <div className="bg-red-500/20 text-red-500 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-red-500/30">
              28B
            </div>
          </div>

          {/* Visual Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-[10px] text-zinc-400 font-mono uppercase tracking-widest mb-2">
              <span>Metadata (85%)</span>
              <span>Value (15%)</span>
            </div>
            <div className="w-full h-4 flex rounded-full overflow-hidden bg-white/5 border border-white/10">
              <div className="h-full bg-red-500/40 w-[85%]" />
              <div className="h-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)] w-[15%]" />
            </div>
          </div>
          
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            Every single number carries 24 bytes of dead weight (type checking, reference counting) before it even stores your actual 4-byte number.
          </p>
        </div>

        {/* NumPy Playcard */}
        <div className="bg-gradient-to-b from-green-500/10 to-transparent border border-green-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden shadow-[0_0_30px_rgba(34,197,94,0.05)]">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-green-500/10 rounded-full blur-2xl" />
          
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-green-400 font-bold uppercase tracking-widest text-lg">NumPy Int</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Static C-Type</span>
            </div>
            <div className="bg-green-500/20 text-green-400 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-green-500/30 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]">
              4B
            </div>
          </div>

          {/* Visual Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-[10px] text-zinc-400 font-mono uppercase tracking-widest mb-2">
              <span>Metadata (0%)</span>
              <span>Value (100%)</span>
            </div>
            <div className="w-full h-4 flex rounded-full overflow-hidden bg-white/5 border border-white/10">
              <div className="h-full bg-green-400 shadow-[0_0_10px_rgba(74,222,128,0.8)] w-full" />
            </div>
          </div>
          
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            Strips away all overhead. It stores exactly what you need—pure raw data directly readable by the CPU hardware.
          </p>
        </div>

      </div>
    </GlassCard>
  );
};
