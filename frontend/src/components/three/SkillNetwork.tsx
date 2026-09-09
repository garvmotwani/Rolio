'use client';

import { useRef, useEffect, useState, useMemo } from 'react';

interface Skill {
  name: string;
  level?: string;
}

interface SkillNetworkProps {
  skills: Skill[];
  className?: string;
}

interface NodeData {
  skill: Skill;
  angle: number;
  radius: number;
  speed: number;
  tilt: number;
  size: number;
}

export default function SkillNetwork({ skills, className = '' }: SkillNetworkProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);
  const [positions, setPositions] = useState<Array<{ x: number; y: number; opacity: number; scale: number }>>([]);

  const nodes = useMemo<NodeData[]>(() => {
    const count = Math.min(skills.length, 10);
    return skills.slice(0, count).map((skill, i) => {
      const isExpert = skill.level === 'expert';
      const isAdvanced = skill.level === 'advanced';
      return {
        skill,
        angle: (i / count) * Math.PI * 2,
        radius: 0.34 + (i % 3) * 0.08,
        speed: 0.12 + (i % 5) * 0.028,
        tilt: 0.25 + (i % 4) * 0.12,
        size: isExpert ? 62 : isAdvanced ? 52 : 42,
      };
    });
  }, [skills]);

  useEffect(() => {
    let lastTime = 0;

    const animate = (time: number) => {
      const dt = lastTime ? (time - lastTime) / 1000 : 0.016;
      lastTime = time;

      const container = containerRef.current;
      if (!container) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }

      const rect = container.getBoundingClientRect();
      const cx = rect.width / 2;
      const cy = rect.height / 2;

      const now = time / 1000;
      const newPositions = nodes.map((node, i) => {
        const currentAngle = node.angle + now * node.speed;
        // radius is a fraction of the container width
        const rx = node.radius * rect.width;
        const ry = node.radius * rect.width * 0.6;
        const x = cx + Math.cos(currentAngle) * rx;
        const y = cy + Math.sin(currentAngle) * ry * Math.cos(currentAngle * node.tilt);
        // Scale based on z-depth for pseudo-3D depth
        const zDepth = Math.sin(currentAngle);
        const scale = 0.78 + zDepth * 0.22;
        const opacity = 0.5 + zDepth * 0.4;
        return { x, y, opacity, scale };
      });

      setPositions(newPositions);
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [nodes]);

  if (skills.length === 0) return null;

  const cx = '50%';
  const cy = '50%';

  return (
    <div ref={containerRef} className={`relative overflow-hidden ${className}`}>
      {/* SVG connections */}
      <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
        {/* Lines from center to each skill */}
        {positions.map((pos, i) => (
          <line
            key={`c-${i}`}
            x1={cx}
            y1={cy}
            x2={`${pos.x}px`}
            y2={`${pos.y}px`}
            stroke="white"
            strokeOpacity={0.04 + pos.opacity * 0.02}
            strokeWidth={0.5}
          />
        ))}
        {/* Lines between nearby skills */}
        {positions.map((pos, i) =>
          positions.slice(i + 1).map((pos2, j) => {
            const dx = pos.x - pos2.x;
            const dy = pos.y - pos2.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 180) {
              return (
                <line
                  key={`s-${i}-${j}`}
                  x1={`${pos.x}px`}
                  y1={`${pos.y}px`}
                  x2={`${pos2.x}px`}
                  y2={`${pos2.y}px`}
                  stroke="white"
                  strokeOpacity={0.02 + (1 - dist / 180) * 0.03}
                  strokeWidth={0.5}
                />
              );
            }
            return null;
          })
        )}
      </svg>

      {/* Center "You" bubble */}
      <div
        className="absolute"
        style={{
          left: cx,
          top: cy,
          transform: 'translate(-50%, -50%)',
          zIndex: 10,
        }}
      >
        {/* Outer glow */}
        <div
          className="absolute rounded-full bg-white/[0.04]"
          style={{
            width: 120,
            height: 120,
            left: -60,
            top: -60,
          }}
        />
        {/* Main bubble */}
        <div
          className="rounded-full border border-white/[0.12] flex items-center justify-center flex-col"
          style={{
            width: 72,
            height: 72,
            marginLeft: -36,
            marginTop: -36,
            background: 'radial-gradient(circle, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 70%, transparent 100%)',
          }}
        >
          <span className="text-sm font-bold text-white/90" style={{ letterSpacing: '0.03em' }}>You</span>
          <span className="text-[7px] font-light text-white/35 uppercase" style={{ letterSpacing: '0.12em' }}>skills</span>
        </div>
      </div>

      {/* Orbiting skill bubbles */}
      {nodes.map((node, i) => {
        const pos = positions[i];
        if (!pos) return null;
        const isExpert = node.skill.level === 'expert';
        const isAdvanced = node.skill.level === 'advanced';

        return (
          <div
            key={i}
            className="absolute"
            style={{
              left: `${pos.x}px`,
              top: `${pos.y}px`,
              transform: `translate(-50%, -50%) scale(${pos.scale})`,
              opacity: pos.opacity,
              zIndex: Math.round(pos.scale * 10),
              transition: 'none',
            }}
          >
            {/* Bubble */}
            <div
              className="rounded-full flex items-center justify-center border"
              style={{
                width: node.size,
                height: node.size,
                borderColor: isExpert ? 'rgba(255,255,255,0.15)' : isAdvanced ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.06)',
                background: isExpert
                  ? 'radial-gradient(circle, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.03) 70%, transparent 100%)'
                  : isAdvanced
                  ? 'radial-gradient(circle, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 70%, transparent 100%)'
                  : 'radial-gradient(circle, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 70%, transparent 100%)',
              }}
            >
              <span
                className="text-center leading-tight px-1.5"
                style={{
                  fontSize: isExpert ? '11px' : isAdvanced ? '10px' : '9px',
                  fontWeight: isExpert ? 600 : 400,
                  color: `rgba(255,255,255,${isExpert ? 0.95 : isAdvanced ? 0.75 : 0.6})`,
                  whiteSpace: 'nowrap',
                  maxWidth: node.size - 6,
                }}
              >
                {node.skill.name}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
