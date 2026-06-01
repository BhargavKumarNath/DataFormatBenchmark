import { motion, AnimatePresence } from 'framer-motion';

export const SimdEngine = ({ isNumPy, simdType, opsPerSecond }) => {
  // Python has 1 block, NumPy has 8 parallel blocks
  const blocks = Array.from({ length: isNumPy ? 8 : 1 }, (_, i) => i);

  return (
    <div className="flex flex-col items-center justify-center h-full w-full">
      <div className="mb-8 text-center relative h-16 w-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={isNumPy ? 'numpy-text' : 'python-text'}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 flex flex-col items-center justify-center"
          >
            <div className={`text-2xl font-bold tracking-tight ${isNumPy ? 'text-blue-400' : 'text-purple-400'}`}>
              {simdType}
            </div>
            <div className="text-zinc-500 text-sm mt-1">
              Throughput: <span className="text-white font-mono">{opsPerSecond}</span>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="relative w-64 h-48 bg-white/5 border border-white/10 rounded-xl overflow-hidden flex flex-col justify-center p-4">
        {/* Track Lines */}
        <div className="absolute inset-0 flex flex-col justify-between py-6 opacity-20">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={`track-${i}`} className="w-full border-t border-white/30 border-dashed" />
          ))}
        </div>

        {/* Moving Blocks */}
        <div className="relative w-full h-full flex flex-col justify-around">
          <AnimatePresence mode="popLayout">
            {blocks.map((block) => (
              <motion.div
                key={isNumPy ? `numpy-block-${block}` : `python-block-${block}`}
                initial={{ x: -40, opacity: 0 }}
                animate={{ 
                  x: ["0%", "400%"], 
                  opacity: [0, 1, 1, 0] 
                }}
                transition={{
                  duration: isNumPy ? 0.4 : 2,
                  repeat: Infinity,
                  ease: "linear",
                  delay: isNumPy ? 0 : 0
                }}
                className={`w-8 h-3 rounded-sm shadow-lg ${isNumPy ? 'bg-blue-400' : 'bg-purple-400'}`}
                style={{
                  boxShadow: isNumPy ? '0 0 10px rgba(96, 165, 250, 0.8)' : 'none'
                }}
              />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
