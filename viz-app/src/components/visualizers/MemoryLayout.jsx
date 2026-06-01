import { motion, AnimatePresence } from 'framer-motion';

export const MemoryLayout = ({ isNumPy, memoryType, memoryUsage }) => {
  // Generate 64 blocks to represent memory
  const blocks = Array.from({ length: 64 }, (_, i) => i);

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
            className="absolute inset-0"
          >
            <div className={`text-2xl font-bold tracking-tight ${isNumPy ? 'text-green-400' : 'text-red-400'}`}>
              {memoryType}
            </div>
            <div className="text-zinc-500 text-sm mt-1">
              Footprint: <span className="text-white font-mono">{memoryUsage}</span>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="relative w-64 h-64 flex items-center justify-center">
        <motion.div 
          layout
          className={`flex flex-wrap items-center justify-center w-full h-full p-2`}
          style={{
            alignContent: isNumPy ? 'center' : 'stretch',
            gap: isNumPy ? '2px' : '12px'
          }}
        >
          {blocks.map((block) => (
            <motion.div
              key={block}
              layout
              transition={{
                type: "spring",
                stiffness: 400,
                damping: 30,
                mass: 0.8
              }}
              animate={{
                backgroundColor: isNumPy ? 'rgb(34 197 94)' : 'rgba(239, 68, 68, 0.8)',
                boxShadow: isNumPy ? '0 0 10px rgba(34, 197, 94, 0.5)' : 'none',
                borderRadius: isNumPy ? '2px' : '50%',
                x: isNumPy ? 0 : (Math.random() * 20 - 10), // slight drift for python
                y: isNumPy ? 0 : (Math.random() * 20 - 10)
              }}
              className="w-4 h-4"
            />
          ))}
        </motion.div>
      </div>
    </div>
  );
};
