'use client';

import { motion } from 'framer-motion';

interface PremiumLoaderProps {
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export default function PremiumLoader({ text = 'Loading...', size = 'md', className = '' }: PremiumLoaderProps) {
  const sizeMap = { sm: 80, md: 120, lg: 180 };
  const s = sizeMap[size];

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className="relative" style={{ width: s, height: s }}>
        {/* Outer ring */}
        <motion.div
          className="absolute inset-0 rounded-full border border-white/[0.06]"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
        />
        {/* Middle ring */}
        <motion.div
          className="absolute inset-[15%] rounded-full border border-white/[0.08]"
          animate={{ rotate: -360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
        {/* Inner pulsing orb */}
        <motion.div
          className="absolute inset-[35%] rounded-full bg-white/[0.08]"
          animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        {/* Glow */}
        <motion.div
          className="absolute inset-[25%] rounded-full"
          style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%)' }}
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      {text && (
        <motion.p
          className="text-xs text-white/25 mt-4 tracking-wide"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {text}
        </motion.p>
      )}
    </div>
  );
}
