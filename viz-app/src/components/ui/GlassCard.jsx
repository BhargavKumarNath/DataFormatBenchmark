export const GlassCard = ({ title, children, className = "" }) => {
  return (
    <div className={`relative overflow-hidden flex flex-col bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-6 transition-all duration-300 ${className}`}>
      {title && (
        <h3 className="text-zinc-400 text-sm uppercase tracking-widest font-semibold mb-6 flex items-center justify-between">
          {title}
        </h3>
      )}
      <div className="flex-1 flex flex-col justify-center">
        {children}
      </div>
    </div>
  );
};
