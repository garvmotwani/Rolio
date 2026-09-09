'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import { motion, AnimatePresence, useScroll, useTransform } from 'framer-motion';
import { Menu, X, Bell, User, LogOut, LayoutDashboard, Search, FileText, Bookmark, Settings, Kanban, Brain, DollarSign, Mail, BarChart3 } from 'lucide-react';
import NotificationBell from './NotificationBell';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
    setUserMenuOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const isLanding = pathname === '/';

  if (isLanding) {
    return <LandingNav />;
  }

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/jobs', label: 'Jobs', icon: Search },
    { href: '/kanban', label: 'Pipeline', icon: Kanban },
    { href: '/applications', label: 'Applications', icon: FileText },
    { href: '/saved', label: 'Saved', icon: Bookmark },
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/salary', label: 'Salary', icon: DollarSign },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[var(--bg-primary)]/85 backdrop-blur-2xl border-b border-[var(--border-primary)]">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
            RO<span className="text-[var(--text-tertiary)]">LIO</span>
          </Link>
          <div className="hidden lg:flex items-center gap-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-[13px] transition-all duration-300 ${
                    active
                      ? 'bg-[var(--bg-active)] text-[var(--text-primary)]'
                      : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                  }`}
                >
                  <Icon size={14} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <NotificationBell />
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-2 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors duration-300 p-1.5 rounded-lg hover:bg-[var(--bg-hover)]"
              aria-expanded={userMenuOpen}
              aria-label="User menu"
            >
              <div className="w-7 h-7 rounded-full bg-[var(--bg-active)] flex items-center justify-center text-[11px] font-semibold border border-[var(--border-primary)]">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <span className="hidden md:inline text-[13px]">{user?.name || 'User'}</span>
            </button>

            <AnimatePresence>
              {userMenuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                  <motion.div
                    initial={{ opacity: 0, y: 8, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 8, scale: 0.96 }}
                    transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    className="absolute right-0 top-full mt-2 w-56 bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded-xl py-1.5 z-50 shadow-2xl shadow-[var(--card-shadow)]"
                  >
                    <div className="px-4 py-3 border-b border-[var(--border-primary)]">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{user?.name}</p>
                      <p className="text-xs text-[var(--text-muted)] mt-0.5">{user?.email}</p>
                    </div>
                    <Link
                      href="/profile"
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      <User size={14} />
                      Profile
                    </Link>
                    <Link
                      href="/settings"
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      <Settings size={14} />
                      Settings
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] w-full transition-colors"
                    >
                      <LogOut size={14} />
                      Sign Out
                    </button>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="lg:hidden bg-[var(--bg-primary)]/95 backdrop-blur-2xl border-t border-[var(--border-primary)] overflow-hidden"
          >
            <div className="px-6 py-4 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(item.href + '/');
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      active ? 'bg-[var(--bg-active)] text-[var(--text-primary)]' : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
                    }`}
                  >
                    <Icon size={16} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

/* ─── Landing Nav (with scroll effects) ─── */
function LandingNav() {
  const { user } = useAuthStore();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const unsub = scrollY.on('change', (v) => setScrolled(v > 30));
    return unsub;
  }, [scrollY]);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? 'bg-[var(--bg-primary)]/80 backdrop-blur-2xl border-b border-[var(--border-primary)]'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
          RO<span className="text-[var(--text-tertiary)]">LIO</span>
        </Link>
        <div className="hidden md:flex items-center gap-8 text-sm text-[var(--text-tertiary)]">
          <a href="#how-it-works" className="hover:text-white/80 transition-colors duration-300">How It Works</a>
          <a href="#features" className="hover:text-white/80 transition-colors duration-300">Features</a>
        </div>
        <div className="hidden md:flex items-center gap-4">
          {user ? (
            <Link href="/dashboard" className="text-sm bg-white text-black px-5 py-2 rounded-full font-medium hover:bg-white/90 transition-all">
              Dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className="text-sm text-white/35 hover:text-white/70 transition-colors duration-300">
                Sign In
              </Link>
              <Link
                href="/signup"
                className="btn-premium text-sm bg-white text-black px-5 py-2 rounded-full font-medium"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors p-1"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="md:hidden bg-[var(--bg-primary)]/95 backdrop-blur-2xl border-t border-[var(--border-primary)] overflow-hidden"
          >
            <div className="px-6 py-5 space-y-4">
              <a href="#how-it-works" className="block text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-sm transition-colors">How It Works</a>
              <a href="#features" className="block text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-sm transition-colors">Features</a>
              <div className="pt-3 border-t border-[var(--border-primary)] space-y-3">
                <Link href="/login" className="block text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-sm transition-colors">Sign In</Link>
                <Link href="/signup" className="block bg-white text-black text-center py-2.5 rounded-full text-sm font-medium">
                  Get Started
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
