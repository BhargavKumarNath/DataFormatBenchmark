import { GlassCard } from '../ui/GlassCard';
import { benchmarkData } from '../../data/benchmarkStats';

const CODE_SNIPPETS = {
  imputation: {
    title: 'Missing Value Imputation',
    python: '[0.0 if x == -99.0 else x for x in amounts]',
    numpy: 'np.where(amounts == -99.0, 0.0, amounts)'
  },
  segmentation: {
    title: 'Customer Risk Segmentation',
    python: `for i in range(N):
    if amt > 5k and age < 12:
        res[i] = 'High-Risk'
    elif ...`,
    numpy: "np.select([(amt > 5k) & (age < 12), ...], ['High-Risk', ...])"
  },
  mathTransform: {
    title: 'Logarithmic Math Transform',
    python: '[math.log(x) if x > 0 else 0.0 for x in scores]',
    numpy: 'np.where(scores > 0, np.log(scores), 0.0)'
  }
};

export const TaskCodeViewer = () => {
  const tasks = ['imputation', 'segmentation', 'mathTransform'];
  const scale = '100M'; // Focus scale for static screenshot

  return (
    <GlassCard title="Compute Code & Time Comparison (100M Rows)" className="w-full mt-8">
      <div className="flex flex-col gap-12 mt-4">
        {tasks.map((taskKey) => {
          const task = CODE_SNIPPETS[taskKey];
          return (
            <div key={taskKey} className="flex flex-col">
              <h4 className="text-zinc-300 font-bold tracking-wide uppercase text-sm mb-4 border-b border-white/10 pb-2">
                {task.title}
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Python View */}
                <div className="bg-black/50 border border-red-500/20 rounded-xl p-6 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-red-400 font-bold tracking-widest text-[10px] uppercase">Naive Python</span>
                      <span className="text-red-400/50 text-[10px] font-mono uppercase tracking-widest">List Comprehension</span>
                    </div>
                    <pre className="font-mono text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                      {task.python}
                    </pre>
                  </div>
                  <div className="mt-6 flex items-end gap-2 border-t border-red-500/10 pt-4">
                    <span className="text-4xl font-mono font-bold text-red-500">
                      {benchmarkData.python.tasks[taskKey][scale]}
                    </span>
                    <span className="text-zinc-500 text-sm font-mono mb-1">ms</span>
                  </div>
                </div>

                {/* NumPy View */}
                <div className="bg-black/50 border border-green-500/20 rounded-xl p-6 flex flex-col justify-between shadow-[0_0_30px_rgba(34,197,94,0.05)]">
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-green-400 font-bold tracking-widest text-[10px] uppercase">NumPy Vectorized</span>
                      <span className="text-green-400/50 text-[10px] font-mono uppercase tracking-widest">C-Optimized</span>
                    </div>
                    <pre className="font-mono text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed">
                      {task.numpy}
                    </pre>
                  </div>
                  <div className="mt-6 flex items-end gap-2 border-t border-green-500/10 pt-4">
                    <span className="text-4xl font-mono font-bold text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]">
                      {benchmarkData.numpy.tasks[taskKey][scale]}
                    </span>
                    <span className="text-zinc-400 text-sm font-mono mb-1">ms</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
};
