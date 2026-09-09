'use client';

import { useRef, useEffect } from 'react';

interface GradientBorderProps {
  children: React.ReactNode;
  className?: string;
  speed?: number;
  borderWidth?: number;
}

export default function GradientBorder({
  children,
  className = '',
  speed = 3,
  borderWidth = 1,
}: GradientBorderProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let animId: number;
    let angle = 0;

    const animate = () => {
      angle += speed;
      el.style.setProperty('--gradient-angle', `${angle}deg`);
      animId = requestAnimationFrame(animate);
    };
    animate();

    return () => cancelAnimationFrame(animId);
  }, [speed]);

  return (
    <div
      ref={containerRef}
      className={`relative rounded-xl ${className}`}
      style={{
        padding: `${borderWidth}px`,
        background: `conic-gradient(from var(--gradient-angle, 0deg), transparent 40%, rgba(255,255,255,0.12) 50%, transparent 60%)`,
      }}
    >
      <div className="relative rounded-[inherit] bg-[#050505]">
        {children}
      </div>
    </div>
  );
}
