'use client';

import { useEffect, useRef } from 'react';

interface Orb {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  opacity: number;
  phase: number;
}

export default function FloatingOrbs({ count = 5, className = '' }: { count?: number; className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;

    const orbs: Orb[] = [];
    for (let i = 0; i < count; i++) {
      orbs.push({
        x: Math.random() * cw,
        y: Math.random() * ch,
        r: 80 + Math.random() * 120,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.1,
        opacity: 0.015 + Math.random() * 0.015,
        phase: Math.random() * Math.PI * 2,
      });
    }

    let time = 0;
    const draw = () => {
      time += 0.005;
      ctx.clearRect(0, 0, cw, ch);

      for (const orb of orbs) {
        orb.x += orb.vx + Math.sin(time + orb.phase) * 0.1;
        orb.y += orb.vy + Math.cos(time * 0.7 + orb.phase) * 0.08;

        // Wrap around
        if (orb.x < -orb.r) orb.x = cw + orb.r;
        if (orb.x > cw + orb.r) orb.x = -orb.r;
        if (orb.y < -orb.r) orb.y = ch + orb.r;
        if (orb.y > ch + orb.r) orb.y = -orb.r;

        const gradient = ctx.createRadialGradient(orb.x, orb.y, 0, orb.x, orb.y, orb.r);
        gradient.addColorStop(0, `rgba(255, 255, 255, ${orb.opacity + Math.sin(time * 0.5 + orb.phase) * 0.005})`);
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.beginPath();
        ctx.arc(orb.x, orb.y, orb.r, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [count]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
    />
  );
}
