'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function KeyboardShortcuts() {
  const [showSearch, setShowSearch] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K → open search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(prev => !prev);
      }
      // Escape → close search
      if (e.key === 'Escape') {
        setShowSearch(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/jobs?q=${encodeURIComponent(query.trim())}`);
      setShowSearch(false);
      setQuery('');
    }
  };

  return (
    <AnimatePresence>
      {showSearch && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowSearch(false)}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9990]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', damping: 30, stiffness: 400 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-[9999] px-4"
          >
            <form onSubmit={handleSubmit} className="bg-[#0a0a0a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
              <div className="flex items-center gap-3 px-5 py-4">
                <Search size={18} className="text-white/30 shrink-0" />
                <input
                  autoFocus
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Search jobs, skills, companies..."
                  className="flex-1 bg-transparent text-white/90 text-sm outline-none placeholder:text-white/20"
                />
                <kbd className="hidden sm:inline text-[10px] text-white/20 bg-white/[0.04] border border-white/[0.06] px-1.5 py-0.5 rounded">
                  ESC
                </kbd>
              </div>
              <div className="border-t border-white/[0.04] px-5 py-3 flex items-center justify-between">
                <div className="flex items-center gap-4 text-[10px] text-white/15">
                  <span><kbd className="bg-white/[0.04] border border-white/[0.06] px-1 rounded">↵</kbd> to search</span>
                  <span><kbd className="bg-white/[0.04] border border-white/[0.06] px-1 rounded">ESC</kbd> to close</span>
                </div>
                <button type="submit" className="text-xs text-white/40 hover:text-white/70 transition-colors">
                  Search →
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
