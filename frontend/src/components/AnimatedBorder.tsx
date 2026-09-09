'use client';

import { useRef, useEffect } from 'react';

interface AnimatedBorderProps {
  children: React.ReactNode;
  className?: string;
  borderWidth?: number;
  speed?: number;
}

export default function AnimatedBorder({
  children,
  className = '',
  borderWidth = 1,
  speed = 3,
}: AnimatedBorderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let angle = 0;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.scale(dpr, dpr);
    };
    resize();

    const resizeObs = new ResizeObserver(resize);
    resizeObs.observe(container);

    const draw = () => {
      const rect = container.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const r = 12; // border-radius

      ctx.clearRect(0, 0, w, h);

      // Rotating gradient along the border
      const cx = w / 2;
      const cy = h / 2;
      const maxDim = Math.max(w, h);

      const gx1 = cx + Math.cos(angle) * maxDim * 0.5;
      const gy1 = cy + Math.sin(angle) * maxDim * 0.5;
      const gx2 = cx + Math.cos(angle + Math.PI) * maxDim * 0.5;
      const gy2 = cy + Math.sin(angle + Math.PI) * maxDim * 0.5;

      const gradient = ctx.createLinearGradient(gx1, gy1, gx2, gy2);
      gradient.addColorStop(0, 'rgba(255, 255, 255, 0.08)');
      gradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.02)');
      gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.12)');
      gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.02)');
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0.08)');

      // Draw rounded rect border
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, r);

      // Create clipping mask for just the border
      ctx.save();
      ctx.clip();
      ctx.clearRect(borderWidth, borderWidth, w - borderWidth * 2, h - borderWidth * 2);
      ctx.restore();

      ctx.strokeStyle = gradient;
      ctx.lineWidth = borderWidth;
      ctx.stroke();

      angle += 0.02 * speed;
      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      resizeObs.disconnect();
    };
  }, [borderWidth, speed]);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-10"
      />
      {children}
    </div>
  );
}
