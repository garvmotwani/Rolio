'use client';

import { motion } from 'framer-motion';

interface AnimatedBeamProps {
  className?: string;
  direction?: 'horizontal' | 'vertical';
  delay?: number;
}

export default function AnimatedBeam({
  className = '',
  direction = 'horizontal',
  delay = 0,
}: AnimatedBeamProps) {
  const isHorizontal = direction === 'horizontal';

  return (
    <div className={`relative ${isHorizontal ? 'h-px w-full' : 'w-px h-full'} ${className}`}>
      {/* Background */}
      <div className="absolute inset-0 bg-white/[0.04]" />
      {/* Animated beam */}
      <motion.div
        className="absolute"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
          ...(isHorizontal
            ? { top: 0, left: 0, height: '100%', width: '40%' }
            : { left: 0, top: 0, width: '100%', height: '40%' }),
        }}
        animate={isHorizontal
          ? { x: ['0%', '250%'] }
          : { y: ['0%', '250%'] }
        }
        transition={{
          duration: 2.5,
          delay,
          repeat: Infinity,
          ease: 'linear',
          repeatDelay: 1,
        }}
      />
    </div>
  );
}
