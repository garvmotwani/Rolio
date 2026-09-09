'use client';

import { useInView } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

interface AnimatedScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export default function AnimatedScoreRing({
  score,
  size = 48,
  strokeWidth = 3,
  className = '',
}: AnimatedScoreRingProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  // Safety net: if IntersectionObserver never fires (throttled/hidden tabs,
  // embeds, quirky browsers), still show the ring instead of an empty track.
  const [fallback, setFallback] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setFallback(true), 1000);
    return () => clearTimeout(t);
  }, []);
  const animate = isInView || fallback;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const isHigh = score >= 80;
  const isMed = score >= 60;

  return (
    <div ref={ref} className={`relative inline-flex items-center justify-center ${className}`}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Animated fill */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={isHigh ? 'rgba(255,255,255,0.85)' : isMed ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.25)'}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={animate ? offset : circumference}
          style={{
            transition: 'stroke-dashoffset 1.2s cubic-bezier(0.16, 1, 0.3, 1)',
            filter: isHigh ? 'drop-shadow(0 0 4px rgba(255,255,255,0.2))' : undefined,
          }}
        />
      </svg>
      <span
        className={`absolute text-[11px] font-semibold ${
          isHigh ? 'text-white' : isMed ? 'text-white/60' : 'text-white/35'
        }`}
      >
        {score}
      </span>
    </div>
  );
}
