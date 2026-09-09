'use client';

import { motion } from 'framer-motion';

const statusStyles: Record<string, { bg: string; text: string; dot: string; glow?: string }> = {
  applied: { bg: 'bg-white/[0.06]', text: 'text-white/50', dot: 'bg-white/40' },
  screening: { bg: 'bg-purple-500/10', text: 'text-purple-300/80', dot: 'bg-purple-400', glow: 'shadow-[0_0_8px_rgba(168,85,247,0.15)]' },
  interview: { bg: 'bg-blue-500/10', text: 'text-blue-300/80', dot: 'bg-blue-400', glow: 'shadow-[0_0_8px_rgba(96,165,250,0.2)]' },
  offer: { bg: 'bg-emerald-500/10', text: 'text-emerald-300/80', dot: 'bg-emerald-400', glow: 'shadow-[0_0_8px_rgba(52,211,153,0.2)]' },
  rejected: { bg: 'bg-red-500/8', text: 'text-red-300/60', dot: 'bg-red-400/60' },
  withdrawn: { bg: 'bg-white/[0.03]', text: 'text-white/25', dot: 'bg-white/15' },
};

interface AnimatedStatusPillProps {
  status: string;
  className?: string;
}

export default function AnimatedStatusPill({ status, className = '' }: AnimatedStatusPillProps) {
  const style = statusStyles[status] || statusStyles.applied;

  return (
    <motion.span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium capitalize ${style.bg} ${style.text} ${style.glow || ''} ${className}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <span className="relative flex h-1.5 w-1.5">
        {status === 'interview' || status === 'screening' ? (
          <span className={`absolute inline-flex h-full w-full rounded-full ${style.dot} opacity-75 animate-ping`} />
        ) : null}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${style.dot}`} />
      </span>
      {status}
    </motion.span>
  );
}
