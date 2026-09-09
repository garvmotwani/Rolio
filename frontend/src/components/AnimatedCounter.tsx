'use client';

import { useEffect, useRef, useState } from 'react';
import { useInView } from 'framer-motion';

interface AnimatedCounterProps {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

export default function AnimatedCounter({
  end,
  duration = 1500,
  suffix = '',
  prefix = '',
  className,
}: AnimatedCounterProps) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-40px' });
  // Latest displayed value so re-animation starts from it (previously the
  // counter froze at its first value when `end` changed).
  const currentRef = useRef(0);
  const animatedRef = useRef(false);

  // Safety net independent of isInView: if the scroll-triggered animation
  // hasn't started within a second (element never marked in view — hidden
  // tabs, throttled/headless environments), set the value directly so the
  // number is never stuck at 0 while the real data says otherwise.
  useEffect(() => {
    const fallback = setTimeout(() => {
      if (!animatedRef.current) {
        animatedRef.current = true;
        currentRef.current = end;
        setCount(end);
      }
    }, 1000);
    return () => clearTimeout(fallback);
  }, [end]);

  useEffect(() => {
    if (!isInView || animatedRef.current) return;
    animatedRef.current = true;
    const from = currentRef.current;
    let raf: number | null = null;

    const startTime = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(from + (end - from) * eased);
      currentRef.current = value;
      setCount(value);
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      if (raf !== null) cancelAnimationFrame(raf);
    };
  }, [isInView, end, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}{count}{suffix}
    </span>
  );
}
