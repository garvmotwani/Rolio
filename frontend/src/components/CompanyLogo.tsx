'use client';

import { useState } from 'react';

interface CompanyLogoProps {
  src?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = {
  sm: 'w-6 h-6 text-[10px]',
  md: 'w-8 h-8 text-xs',
  lg: 'w-10 h-10 text-sm',
};

export default function CompanyLogo({ src, name, size = 'md', className = '' }: CompanyLogoProps) {
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);

  const showImage = src && !imgError;
  const initials = name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      className={`relative rounded-md bg-white/[0.06] flex items-center justify-center font-medium text-white/50 overflow-hidden ${sizeMap[size]} ${className}`}
    >
      {showImage && (
        <img
          src={src}
          alt={`${name} logo`}
          className="w-full h-full object-contain p-0.5"
          onError={() => setImgError(true)}
          onLoad={() => setImgLoaded(true)}
          style={{ opacity: imgLoaded ? 1 : 0, transition: 'opacity 0.2s' }}
        />
      )}
      {(!showImage || !imgLoaded) && (
        <span className="absolute inset-0 flex items-center justify-center">{initials}</span>
      )}
    </div>
  );
}
