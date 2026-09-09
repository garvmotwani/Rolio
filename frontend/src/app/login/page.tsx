'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/lib/store';
import { startGoogleSignIn, GoogleIcon } from '@/lib/googleAuth';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2, Mail, Lock } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import MagneticButton from '@/components/MagneticButton';
import AnimatedBorder from '@/components/AnimatedBorder';

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [googleLoading, setGoogleLoading] = useState(false);
  const { login, isLoading } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Show a friendly message when Google redirects back with an error
  useEffect(() => {
    if (searchParams.get('google') === 'error') {
      setError('Google sign-in failed or expired. Please try again.');
      // Clean the param so a manual refresh doesn’t re-show it
      window.history.replaceState({}, '', '/login');
    }
  }, [searchParams]);

  const handleGoogleSignIn = async () => {
    setError('');
    setGoogleLoading(true);
    try {
      await startGoogleSignIn();
      // Navigation to Google happens via full page redirect
    } catch {
      setError('Google sign-in is unavailable right now');
      setGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    const result = await login(email, password);
    if (result.success) {
      router.push('/dashboard');
    } else {
      setError(result.error || 'Login failed');
    }
  };

  const formItems = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.15 },
    },
  };

  const formItem = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative">
      {/* Background effects */}
      <FloatingOrbs count={3} className="opacity-30" />
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-white/[0.01] rounded-full blur-[100px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md relative z-10"
      >
        <AnimatedBorder className="rounded-2xl" speed={1.5}>
          <div className="bg-black rounded-2xl px-8 py-10 md:px-10">
        <motion.div variants={formItem} initial="hidden" animate="show">
          <Link href="/" className="text-xl font-bold tracking-tight inline-block mb-10">
            RO<span className="text-white/30">LIO</span>
          </Link>
          <h1 className="text-4xl font-bold tracking-tight">Welcome back</h1>
          <p className="text-sm text-white/30 mt-3">Sign in to your account</p>
        </motion.div>

        <motion.form
          onSubmit={handleSubmit}
          className="space-y-5 mt-10"
          variants={formItems}
          initial="hidden"
          animate="show"
        >
          <motion.div variants={formItem}>
            <label className="block text-[11px] text-white/25 mb-2 uppercase tracking-wider">Email</label>
            <div className="relative">
              <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                className="!pl-10"
              />
            </div>
          </motion.div>
          <motion.div variants={formItem}>
            <label className="block text-[11px] text-white/25 mb-2 uppercase tracking-wider">Password</label>
            <div className="relative">
              <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="!pl-10"
              />
            </div>
          </motion.div>

          {error && (
            <motion.p
              initial={{ opacity: 0, y: -5, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="text-sm text-white/60 bg-white/5 border border-white/10 rounded-lg px-4 py-3"
            >
              {error}
            </motion.p>
          )}

          <motion.div variants={formItem}>
            <MagneticButton type="submit" disabled={isLoading || googleLoading} className="btn-premium btn-glow w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50">
              {isLoading ? <Loader2 size={16} className="animate-spin" /> : null}
              Sign In
              {!isLoading && <ArrowRight size={16} />}
            </MagneticButton>
          </motion.div>

          <motion.div variants={formItem} className="flex items-center gap-4 py-1">
            <span className="h-px flex-1 bg-white/[0.06]" />
            <span className="text-[10px] uppercase tracking-wider text-white/20">or</span>
            <span className="h-px flex-1 bg-white/[0.06]" />
          </motion.div>

          <motion.div variants={formItem}>
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={isLoading || googleLoading}
              className="w-full bg-white/[0.04] border border-white/[0.08] text-white/80 py-3.5 rounded-full font-medium text-sm flex items-center justify-center gap-2.5 hover:bg-white/[0.07] hover:text-white hover:border-white/[0.14] transition-all disabled:opacity-50"
            >
              {googleLoading ? <Loader2 size={16} className="animate-spin" /> : <GoogleIcon size={16} />}
              Continue with Google
            </button>
          </motion.div>
        </motion.form>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="text-center text-sm text-white/20 mt-10"
        >
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-white/50 hover:text-white/80 transition-colors underline underline-offset-4 decoration-white/15 hover:decoration-white/40">
            Create one
          </Link>
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          className="mt-8 p-4 border border-white/[0.04] rounded-xl bg-white/[0.01]"
        >
          <p className="text-[10px] text-white/20 mb-1.5 uppercase tracking-wider">Demo credentials</p>
          <p className="text-xs text-white/40 font-mono">demo@rolio.com / password</p>
        </motion.div>
          </div>
        </AnimatedBorder>
      </motion.div>
    </div>
  );
}
