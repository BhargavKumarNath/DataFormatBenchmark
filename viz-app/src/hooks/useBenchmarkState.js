import { useState, useMemo } from 'react';
import { benchmarkData } from '../data/benchmarkStats';

export const useBenchmarkState = () => {
  const [activeFramework, setActiveFramework] = useState('python'); // 'python' | 'numpy'
  const [dataScale, setDataScale] = useState('1M'); // '1M' | '10M' | '100M'

  const currentStats = useMemo(() => {
    const fwData = benchmarkData[activeFramework];
    return {
      memoryType: fwData.memory.type,
      memoryUsage: fwData.memory[dataScale],
      cacheL1L2HitRate: fwData.cache.l1l2HitRate,
      cacheDescription: fwData.cache.description,
      simdType: fwData.simd.type,
      opsPerSecond: fwData.simd.opsPerSecond,
      tasks: {
        imputation: fwData.tasks.imputation[dataScale],
        segmentation: fwData.tasks.segmentation[dataScale],
        mathTransform: fwData.tasks.mathTransform[dataScale]
      }
    };
  }, [activeFramework, dataScale]);

  return {
    activeFramework,
    setActiveFramework,
    dataScale,
    setDataScale,
    currentStats
  };
};
