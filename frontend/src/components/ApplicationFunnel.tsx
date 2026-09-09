'use client';

import { motion } from 'framer-motion';

interface FunnelStage {
  label: string;
  count: number;
  color: string;
  percentage: number;
}

export default function ApplicationFunnel({ stages }: { stages: FunnelStage[] }) {
  const maxCount = Math.max(...stages.map(s => s.count), 1);

  return (
    <div className="space-y-3">
      {stages.map((stage, i) => (
        <motion.div
          key={stage.label}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.1, type: 'spring', damping: 20 }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${stage.color}`} />
              <span className="text-xs text-white/60">{stage.label}</span>
            </div>
            <span className="text-xs font-medium text-white/80">{stage.count}</span>
          </div>
          <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.max((stage.count / maxCount) * 100, 2)}%` }}
              transition={{ delay: i * 0.1 + 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
              className={`h-full rounded-full ${stage.color.replace('bg-', 'bg-')}`}
              style={{ opacity: 0.7 + (i * 0.05) }}
            />
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export function WeeklyActivity({ data }: { data: number[] }) {
  const max = Math.max(...data, 1);
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <div className="flex items-end justify-between gap-1.5 h-24">
      {data.map((val, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: `${(val / max) * 100}%` }}
            transition={{ delay: i * 0.05, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="w-full bg-white/20 hover:bg-white/30 rounded-t-md transition-colors min-h-[2px]"
          />
          <span className="text-[9px] text-white/25">{days[i]}</span>
        </div>
      ))}
    </div>
  );
}

export function ResponseRateRing({ rate, size = 80 }: { rate: number; size?: number }) {
  const circumference = 2 * Math.PI * 34;
  const strokeDashoffset = circumference - (rate / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={34}
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={4}
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={34}
          stroke="white"
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
          style={{ strokeDasharray: circumference }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-semibold text-white/90">{rate}%</span>
      </div>
    </div>
  );
}
