'use client';

import { useRef, useState, useCallback } from 'react';

interface MagneticButtonProps {
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
  strength?: number;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
}

export default function MagneticButton({
  children,
  href,
  onClick,
  className = '',
  strength = 0.25,
  type = 'button',
  disabled,
}: MagneticButtonProps) {
  const ref = useRef<HTMLElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const handleMouse = useCallback((e: React.MouseEvent) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    setOffset({ x: x * strength, y: y * strength });
  }, [strength]);

  const reset = useCallback(() => setOffset({ x: 0, y: 0 }), []);

  const style = {
    transform: `translate(${offset.x}px, ${offset.y}px)`,
    transition: 'transform 0.4s cubic-bezier(0.03, 0.98, 0.52, 0.99)',
  };

  const sharedProps = {
    ref: ref as any,
    className,
    onMouseMove: handleMouse,
    onMouseLeave: reset,
    style,
    onClick,
    disabled,
  };

  if (href) {
    const Link = require('next/link').default;
    return <Link href={href} {...sharedProps}>{children}</Link>;
  }

  return <button type={type} {...sharedProps}>{children}</button>;
}
