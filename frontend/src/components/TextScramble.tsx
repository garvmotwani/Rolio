'use client';

import { useEffect, useRef, useState } from 'react';

interface TextScrambleProps {
  text: string;
  className?: string;
  speed?: number;
  delay?: number;
}

const chars = '!<>-_\\/[]{}—=+*^?#________';

export default function TextScramble({ text, className = '', speed = 30, delay = 0 }: TextScrambleProps) {
  const [display, setDisplay] = useState('');
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started) return;

    let timeoutId: NodeJS.Timeout;
    let frameId: number;
    const queue: { from: string; to: string; start: number; end: number }[] = [];

    for (let i = 0; i < text.length; i++) {
      queue.push({
        from: chars[Math.floor(Math.random() * chars.length)],
        to: text[i],
        start: Math.floor(Math.random() * 20),
        end: Math.floor(Math.random() * 20) + 15,
      });
    }

    let frame = 0;
    const update = () => {
      let output = '';
      let complete = 0;

      for (let i = 0; i < queue.length; i++) {
        const { from, to, start, end } = queue[i];
        if (frame >= end) {
          complete++;
          output += to;
        } else if (frame >= start) {
          output += chars[Math.floor(Math.random() * chars.length)];
        } else {
          output += from;
        }
      }

      setDisplay(output);

      if (complete === queue.length) {
        cancelAnimationFrame(frameId);
      } else {
        frame++;
        frameId = requestAnimationFrame(update);
      }
    };

    timeoutId = setTimeout(() => {
      frameId = requestAnimationFrame(update);
    }, delay);

    return () => {
      clearTimeout(timeoutId);
      cancelAnimationFrame(frameId);
    };
  }, [started, text, speed, delay]);

  return (
    <span ref={ref} className={className}>
      {display || text}
    </span>
  );
}
