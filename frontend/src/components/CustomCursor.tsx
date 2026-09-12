'use client';

import { useEffect, useRef, useState } from 'react';

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [isHovering, setIsHovering] = useState(false);
  const [isMagnetic, setIsMagnetic] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const pos = useRef({ x: -100, y: -100 });
  const ringPos = useRef({ x: -100, y: -100 });
  // Mirrors the hover/magnetic scale for the rAF loop (state → ref so the
  // animation loop reads a plain number instead of touching the DOM).
  const scaleRef = useRef(1);

  useEffect(() => {
    scaleRef.current = isMagnetic ? 1.5 : isHovering ? 2.5 : 1;
  }, [isHovering, isMagnetic]);

  useEffect(() => {
    // Only on desktop
    if (window.matchMedia('(pointer: coarse)').matches) return;
    if (window.innerWidth < 768) return;

    setIsVisible(true);

    // All positioning goes through transform (GPU-composited, no layout).
    // Writes are batched into one rAF loop instead of style writes inside
    // mousemove (which fire faster than frames).
    let pendingDot = false;
    const handleMouseMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
      pendingDot = true;
    };

    const handleMouseEnter = () => setIsVisible(true);
    const handleMouseLeave = () => setIsVisible(false);

    // Snappy ring follow: 0.35 per frame at 60fps ≈ 63ms to ~90% of the
    // cursor distance. The old 0.12 lagged visibly (~400ms behind).
    let animId: number;
    const animateRing = () => {
      ringPos.current.x += (pos.current.x - ringPos.current.x) * 0.35;
      ringPos.current.y += (pos.current.y - ringPos.current.y) * 0.35;
      // Snap when close enough — kills the trailing "rubber band" micro-jitter
      if (Math.abs(pos.current.x - ringPos.current.x) < 0.1) ringPos.current.x = pos.current.x;
      if (Math.abs(pos.current.y - ringPos.current.y) < 0.1) ringPos.current.y = pos.current.y;
      if (dotRef.current) {
        dotRef.current.style.transform =
          `translate3d(${pos.current.x}px, ${pos.current.y}px, 0) translate(-50%, -50%) scale(${scaleRef.current})`;
      }
      if (ringRef.current) {
        ringRef.current.style.transform =
          `translate3d(${ringPos.current.x}px, ${ringPos.current.y}px, 0) translate(-50%, -50%)`;
      }
      pendingDot = false;
      animId = requestAnimationFrame(animateRing);
    };
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

    document.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseenter', handleMouseEnter);
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseover', handleEnterInteractive);
    document.addEventListener('mouseout', handleLeaveInteractive);

    // Find magnetic elements (re-query on DOM changes — pages mount/unmount)
    let magneticEls: Element[] = [];
    const bindMagnetic = () => {
      magneticEls.forEach(el => {
        el.removeEventListener('mouseenter', handleMagneticEnter);
        el.removeEventListener('mouseleave', handleMagneticLeave);
      });
      magneticEls = Array.from(document.querySelectorAll('[data-magnetic]'));
      magneticEls.forEach(el => {
        el.addEventListener('mouseenter', handleMagneticEnter);
        el.addEventListener('mouseleave', handleMagneticLeave);
      });
    };
    bindMagnetic();
    const mo = new MutationObserver(bindMagnetic);
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      cancelAnimationFrame(animId);
      mo.disconnect();
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
        style={{ opacity: 1, transform: 'translate3d(-100px, -100px, 0) translate(-50%, -50%)' }}
      />
      <div
        ref={ringRef}
        className={`cursor-ring ${isHovering ? 'cursor-hover' : ''} ${isMagnetic ? 'cursor-magnetic' : ''}`}
        style={{ opacity: 1, transform: 'translate3d(-100px, -100px, 0) translate(-50%, -50%)' }}
      />
    </>
  );
}
