import { motion, AnimatePresence } from 'framer-motion';

export const CacheGauge = ({ isNumPy, hitRate, description }) => {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (hitRate / 100) * circumference;

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
            <div className={`text-2xl font-bold tracking-tight ${isNumPy ? 'text-green-400' : 'text-orange-500'}`}>
              {hitRate}% Hit Rate
            </div>
            <div className="text-zinc-500 text-sm mt-1 max-w-[200px] leading-tight">
              {description}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="relative flex items-center justify-center">
        <svg width="200" height="200" className="transform -rotate-90 drop-shadow-xl">
          {/* Background Track */}
          <circle
            cx="100"
            cy="100"
            r={radius}
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth="16"
            fill="none"
          />
          {/* Animated Fill */}
          <motion.circle
            cx="100"
            cy="100"
            r={radius}
            stroke={isNumPy ? '#4ade80' : '#f97316'}
            strokeWidth="16"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ 
              strokeDashoffset,
              filter: isNumPy ? 'drop-shadow(0 0 12px rgba(74, 222, 128, 0.8))' : 'none'
            }}
            transition={{
              type: "spring",
              stiffness: 40,
              damping: 12,
              duration: 1.5
            }}
            style={{
              // Add jitter for python
              transformOrigin: "center",
              animation: !isNumPy ? "jitter 0.2s infinite alternate" : "none"
            }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.span 
            className={`text-4xl font-mono font-bold ${isNumPy ? 'text-green-400' : 'text-orange-500'}`}
            animate={{ scale: isNumPy ? [1, 1.1, 1] : 1 }}
            transition={{ duration: 0.5 }}
          >
            {hitRate}%
          </motion.span>
        </div>
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes jitter {
          0% { transform: rotate(-1deg) scale(0.99); }
          100% { transform: rotate(1deg) scale(1.01); }
        }
      `}} />
    </div>
  );
};
