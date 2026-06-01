import liveResults from '../../data/live_results.json';
import { GlassCard } from '../ui/GlassCard';

export const StorageCards = () => {
  const { parquet_mb, csv_mb, size_ratio } = liveResults.dataset;

  return (
    <GlassCard title="1. File Storage: Text vs Binary" className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-4">

        {/* CSV Card */}
        <div className="bg-gradient-to-b from-red-500/10 to-transparent border border-red-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-red-500/10 rounded-full blur-2xl" />
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-red-400 font-bold uppercase tracking-widest text-lg">CSV File</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Unstructured Text</span>
            </div>
            <div className="bg-red-500/20 text-red-500 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-red-500/30">
              {csv_mb >= 1024 ? `${(csv_mb / 1024).toFixed(1)} GB` : `${csv_mb.toFixed(0)} MB`}
            </div>
          </div>
          <div className="mb-4">
            <div className="bg-black/50 border border-red-500/20 rounded-lg p-3 font-mono text-[10px] text-zinc-500 break-all leading-relaxed h-24 overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/80 z-10" />
              model_run_sha256,framework,optimizer_type,...<br />
              a3f9c12d,PyTorch,AdamW,CrossEntropy,...<br />
              b7e2a89f,TensorFlow,SGD,MSE,...<br />
              c1d4f567,JAX,RMSprop,Huber,...
            </div>
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            <strong className="text-red-400">Raw text on disk.</strong> The CPU must decode every character from ASCII before processing. Every comma must be parsed.
          </p>
        </div>

        {/* Parquet Card */}
        <div className="bg-gradient-to-b from-green-500/10 to-transparent border border-green-500/20 rounded-2xl p-6 flex flex-col relative overflow-hidden shadow-[0_0_30px_rgba(34,197,94,0.05)]">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-green-500/10 rounded-full blur-2xl" />
          <div className="flex justify-between items-start mb-8">
            <div>
              <h4 className="text-green-400 font-bold uppercase tracking-widest text-lg">Parquet File</h4>
              <span className="text-zinc-500 text-xs font-mono uppercase tracking-widest">Columnar Binary</span>
            </div>
            <div className="bg-green-500/20 text-green-400 font-mono font-bold text-xl px-4 py-2 rounded-xl border border-green-500/30 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]">
              {parquet_mb >= 1024 ? `${(parquet_mb / 1024).toFixed(1)} GB` : `${parquet_mb.toFixed(0)} MB`}
            </div>
          </div>
          <div className="mb-4 flex gap-2 h-24">
            {['sha256\n(Dict)', 'framework\n(Dict)', 'train_loss\n(F32)', 'val_acc\n(F32)'].map((col, i) => (
              <div key={i} className={`flex-1 border rounded-lg flex flex-col overflow-hidden ${i === 2 || i === 3 ? 'border-green-400/50 bg-green-500/20 shadow-[0_0_12px_rgba(34,197,94,0.2)]' : 'border-green-500/20 bg-green-500/10'}`}>
                <div className={`text-[7px] text-center font-bold py-1 whitespace-pre-line leading-tight px-1 ${i === 2 || i === 3 ? 'bg-green-500 text-black' : 'bg-green-500/30 text-green-300'}`}>{col}</div>
                <div className="flex-1 flex items-center justify-center text-green-500/60 text-[9px] font-mono">RAW</div>
              </div>
            ))}
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed mt-auto">
            <strong className="text-green-400">{size_ratio}x smaller than CSV.</strong> Stored as pure binary, grouped by column. The CPU streams it directly — zero decoding overhead.
          </p>
        </div>

      </div>
    </GlassCard>
  );
};
