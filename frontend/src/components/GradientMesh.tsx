'use client';

import { useEffect, useRef } from 'react';

interface GradientMeshProps {
  className?: string;
  intensity?: number;
  colors?: string[];
}

export default function GradientMesh({
  className = '',
  intensity = 1,
  colors = [
    'rgba(255, 255, 255, 0.03)',
    'rgba(255, 255, 255, 0.02)',
    'rgba(255, 255, 255, 0.04)',
    'rgba(255, 255, 255, 0.015)',
  ],
}: GradientMeshProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let time = 0;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener('resize', resize);

    const cw = () => canvas.offsetWidth;
    const ch = () => canvas.offsetHeight;

    interface Blob {
      x: number;
      y: number;
      r: number;
      vx: number;
      vy: number;
      color: string;
      phase: number;
    }

    const blobs: Blob[] = [];
    for (let i = 0; i < 5; i++) {
      blobs.push({
        x: Math.random() * cw(),
        y: Math.random() * ch(),
        r: 150 + Math.random() * 200,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.2,
        color: colors[i % colors.length],
        phase: Math.random() * Math.PI * 2,
      });
    }

    const draw = () => {
      time += 0.003;
      const w = cw();
      const h = ch();
      ctx.clearRect(0, 0, w, h);

      for (const blob of blobs) {
        blob.x += blob.vx + Math.sin(time + blob.phase) * 0.4;
        blob.y += blob.vy + Math.cos(time * 0.7 + blob.phase) * 0.3;

        // Wrap around with padding
        const pad = blob.r;
        if (blob.x < -pad) blob.x = w + pad;
        if (blob.x > w + pad) blob.x = -pad;
        if (blob.y < -pad) blob.y = h + pad;
        if (blob.y > h + pad) blob.y = -pad;

        // Breathing effect
        const breathR = blob.r + Math.sin(time * 0.8 + blob.phase) * 30;

        const gradient = ctx.createRadialGradient(
          blob.x, blob.y, 0,
          blob.x, blob.y, breathR
        );
        gradient.addColorStop(0, blob.color);
        gradient.addColorStop(0.5, blob.color.replace(/[\d.]+\)$/, `${parseFloat(blob.color.match(/[\d.]+\)$/)?.[0] || '0.03') * 0.5})`));
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

        ctx.beginPath();
        ctx.arc(blob.x, blob.y, breathR, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();
      }

      // Add subtle grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.008)';
      ctx.lineWidth = 1;
      const gridSize = 60;
      for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [colors, intensity]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
      style={{ opacity: intensity }}
    />
  );
}
