'use client';

import { useEffect, useRef, useState } from 'react';

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [isHovering, setIsHovering] = useState(false);
  const [isMagnetic, setIsMagnetic] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const pos = useRef({ x: 0, y: 0 });
  const ringPos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    // Only on desktop
    if (window.matchMedia('(pointer: coarse)').matches) return;
    if (window.innerWidth < 768) return;

    setIsVisible(true);

    const handleMouseMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
      if (dotRef.current) {
        dotRef.current.style.left = `${e.clientX}px`;
        dotRef.current.style.top = `${e.clientY}px`;
      }
    };

    const handleMouseEnter = () => setIsVisible(true);
    const handleMouseLeave = () => setIsVisible(false);

    // Smooth ring follow
    let animId: number;
    const animateRing = () => {
      ringPos.current.x += (pos.current.x - ringPos.current.x) * 0.12;
      ringPos.current.y += (pos.current.y - ringPos.current.y) * 0.12;
      if (ringRef.current) {
        ringRef.current.style.left = `${ringPos.current.x}px`;
        ringRef.current.style.top = `${ringPos.current.y}px`;
      }
      animId = requestAnimationFrame(animateRing);
    };
    ringPos.current = { x: pos.current.x, y: pos.current.y };
    animateRing();

    const handleEnterInteractive = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('a, button, [role="button"], input, textarea, select, label')) {
        setIsHovering(true);
      }
    };

    const handleLeaveInteractive = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('a, button, [role="button"], input, textarea, select, label')) {
        setIsHovering(false);
      }
    };

    const handleMagneticEnter = () => setIsMagnetic(true);
    const handleMagneticLeave = () => setIsMagnetic(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseenter', handleMouseEnter);
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseover', handleEnterInteractive);
    document.addEventListener('mouseout', handleLeaveInteractive);

    // Find magnetic elements
    const magneticEls = document.querySelectorAll('[data-magnetic]');
    magneticEls.forEach(el => {
      el.addEventListener('mouseenter', handleMagneticEnter);
      el.addEventListener('mouseleave', handleMagneticLeave);
    });

    return () => {
      cancelAnimationFrame(animId);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseenter', handleMouseEnter);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseover', handleEnterInteractive);
      document.removeEventListener('mouseout', handleLeaveInteractive);
      magneticEls.forEach(el => {
        el.removeEventListener('mouseenter', handleMagneticEnter);
        el.removeEventListener('mouseleave', handleMagneticLeave);
      });
    };
  }, []);

  if (!isVisible) return null;

  return (
    <>
      <div
        ref={dotRef}
        className="cursor-dot"
        style={{ opacity: 1 }}
      />
      <div
        ref={ringRef}
        className={`cursor-ring ${isHovering ? 'cursor-hover' : ''} ${isMagnetic ? 'cursor-magnetic' : ''}`}
        style={{ opacity: 1 }}
      />
    </>
  );
}
