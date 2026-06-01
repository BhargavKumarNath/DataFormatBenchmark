import { GlassCard } from '../ui/GlassCard';
import predicateData from '../../data/predicate_results.json';

export const PredicatePushdown = () => {
  const { query, files, results, io_reduction_pct, speedup } = predicateData;

  const polarsResult    = results.find(r => r.engine === 'Polars' && r.format === 'Parquet');
  const pandasCsvResult = results.find(r => r.engine === 'Pandas' && r.format === 'CSV');
  const maxDiskRead     = Math.max(...results.map(r => r.disk_read_mb || 0));

  const colGroups = Array.from({ length: query.total_cols }, (_, i) => ({
    i,
    selected: i < query.selected_cols,
    label: query.select_cols[i] ?? `col_${i}`,
  }));

  return (
    <GlassCard className="w-full border border-white/5 bg-gradient-to-br from-black/90 to-zinc-900/60">
      {/* Header */}
      <div className="p-6 md:p-8 border-b border-white/5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.8)]" />
              <span className="text-violet-400 text-[10px] font-mono uppercase tracking-widest font-bold">Advanced: Predicate Pushdown</span>
            </div>
            <h3 className="text-white text-xl font-bold tracking-tight">The Query That Changes Everything</h3>
            <p className="text-zinc-400 text-xs mt-1 max-w-lg">
              Same query. Same result. But one engine reads the entire file. The other skips 90% of it — before data even leaves your SSD.
            </p>
          </div>
          <div className="flex gap-4 flex-shrink-0">
            <div className="text-center bg-violet-500/10 border border-violet-500/20 rounded-xl px-5 py-3">
              <div className="text-violet-400 font-mono font-bold text-2xl">{io_reduction_pct}%</div>
              <div className="text-zinc-500 text-[10px] uppercase tracking-widest mt-0.5">Less I/O</div>
            </div>
            <div className="text-center bg-green-500/10 border border-green-500/20 rounded-xl px-5 py-3">
              <div className="text-green-400 font-mono font-bold text-2xl">{speedup}x</div>
              <div className="text-zinc-500 text-[10px] uppercase tracking-widest mt-0.5">Faster</div>
            </div>
          </div>
        </div>

        {/* Query block */}
        <div className="mt-5 bg-black/60 border border-white/10 rounded-xl p-4 flex flex-col md:flex-row gap-4 items-start">
          <div className="flex-1">
            <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mb-2">Analytical Query</div>
            <code className="text-violet-300 font-mono text-sm leading-relaxed block">
              df<br />
              {'  '}.filter( <span className="text-yellow-400">framework == &quot;PyTorch&quot;</span><br />
              {'          '}& <span className="text-yellow-400">validation_accuracy &gt; 0.90</span> )<br />
              {'  '}.select( <span className="text-green-400">{query.select_cols.join(', ')}</span> )
            </code>
          </div>
          <div className="flex-shrink-0 text-center border-l border-white/10 pl-6 hidden md:flex md:flex-col md:justify-center">
            <div className="text-zinc-300 font-mono font-bold text-2xl">
              {query.rows_matched.toLocaleString()}
            </div>
            <div className="text-zinc-600 text-[10px] uppercase tracking-widest mt-0.5">Rows Matched</div>
            <div className="text-zinc-700 text-[10px] font-mono mt-1">same for all engines</div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="p-6 md:p-8 space-y-8">

        {/* Column pruning visualizer */}
        <div>
          <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono mb-3">
            Column Pruning — {query.selected_cols} of {query.total_cols} columns requested
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {colGroups.map(({ i, selected, label }) => (
              <div
                key={i}
                className={`h-8 rounded flex items-center justify-center text-[9px] font-mono font-bold ${
                  selected
                    ? 'bg-green-500 text-black shadow-[0_0_10px_rgba(34,197,94,0.4)] px-3'
                    : 'bg-white/5 text-zinc-700 border border-white/10 px-2'
                }`}
              >
                {selected ? label : `col_${i}`}
              </div>
            ))}
          </div>
          <p className="text-zinc-600 text-[10px] mt-2 font-mono">
            <span className="text-green-400">■</span> Parquet reads only these {query.selected_cols} columns from disk &nbsp;·&nbsp;
            <span className="text-zinc-700">■</span> CSV reads all {query.total_cols} — then throws {query.total_cols - query.selected_cols} away
          </p>
        </div>

        {/* Disk I/O bars */}
        <div className="space-y-5">
          <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">
            Actual Bytes Read from Disk (measured via psutil)
          </div>

          {results.map((r) => {
            const pct = Math.max((r.disk_read_mb / maxDiskRead) * 100, 1.5);
            return (
              <div key={r.engine + r.format}>
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: r.color, boxShadow: `0 0 6px ${r.color}80` }} />
                    <span className="text-zinc-200 text-sm font-bold">{r.engine} + {r.format}</span>
                    {r.engine === 'Polars' && r.format === 'Parquet' && (
                      <span className="text-[8px] bg-violet-500/20 text-violet-400 border border-violet-500/30 px-1.5 py-0.5 rounded font-mono uppercase tracking-widest">
                        PUSHDOWN ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-500 text-[10px] font-mono">{r.elapsed_s.toFixed(2)}s</span>
                    <span className="font-mono font-bold text-base" style={{ color: r.color }}>
                      {r.disk_read_mb >= 1024
                        ? `${(r.disk_read_mb / 1024).toFixed(2)} GB`
                        : `${r.disk_read_mb.toFixed(0)} MB`}
                    </span>
                  </div>
                </div>
                <div className="w-full h-5 bg-white/5 border border-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: r.color,
                      boxShadow: `0 0 12px ${r.color}50`,
                    }}
                  />
                </div>
                <p className="text-zinc-600 text-[10px] font-mono mt-1 italic">{r.strategy}</p>
              </div>
            );
          })}
        </div>

        {/* The Insight callout */}
        {polarsResult && pandasCsvResult && (
          <div className="bg-violet-500/5 border border-violet-500/20 rounded-xl p-5">
            <div className="text-violet-400 text-[10px] font-mono uppercase tracking-widest mb-3">The Insight</div>
            <p className="text-zinc-300 text-sm leading-relaxed">
              Polars pushed the filter <strong className="text-white">down to the Parquet storage layer</strong>, before any data entered RAM.
              It told the reader: <span className="text-yellow-300 font-mono text-xs">"Only decompress row groups where framework = PyTorch."</span>
              {' '}The result?&nbsp;
              <strong className="text-green-400">
                {polarsResult.disk_read_mb >= 1024
                  ? `${(polarsResult.disk_read_mb / 1024).toFixed(2)}GB`
                  : `${polarsResult.disk_read_mb.toFixed(0)}MB`} read
              </strong>{' '}instead of{' '}
              <strong className="text-red-400">
                {pandasCsvResult.disk_read_mb >= 1024
                  ? `${(pandasCsvResult.disk_read_mb / 1024).toFixed(2)}GB`
                  : `${pandasCsvResult.disk_read_mb.toFixed(0)}MB`}
              </strong>.{' '}
              Pandas had no choice — CSV has no index, no metadata, no structure. It read everything.
            </p>
          </div>
        )}

      </div>
    </GlassCard>
  );
};
