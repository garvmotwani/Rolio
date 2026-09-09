'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2, Lock, CheckCircle2, XCircle } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import AnimatedBorder from '@/components/AnimatedBorder';
import { apiPost } from '@/lib/api';

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetForm />
    </Suspense>
  );
}

function ResetForm() {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  // A missing token means the link is malformed — treat as invalid immediately
  useEffect(() => {
    if (!token) {
      setError('This reset link is invalid. Please request a new one.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (isLoading) return;
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setIsLoading(true);
    try {
      await apiPost('/api/auth/reset-password', { token, password });
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed. The link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  const formItems = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
  };

  const formItem = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
  };

  const invalid = !!error && !success && !password && !confirm;

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative">
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
              {success ? (
                <>
                  <h1 className="text-4xl font-bold tracking-tight">All set</h1>
                  <p className="text-sm text-white/30 mt-3">Your password has been updated.</p>
                </>
              ) : (
                <>
                  <h1 className="text-4xl font-bold tracking-tight">Set a new password</h1>
                  <p className="text-sm text-white/30 mt-3">
                    Choose a strong password — at least 8 characters.
                  </p>
                </>
              )}
            </motion.div>

            {success ? (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="mt-10 space-y-5"
              >
                <div className="flex items-start gap-3 p-4 border border-white/[0.06] rounded-xl bg-white/[0.02]">
                  <CheckCircle2 size={18} className="text-white/60 mt-0.5 shrink-0" />
                  <p className="text-sm text-white/50 leading-relaxed">
                    For security, you&apos;ve been signed out of all devices. Sign in with
                    your new password to continue.
                  </p>
                </div>
                <button
                  onClick={() => router.push('/login')}
                  className="btn-premium w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2"
                >
                  Sign in
                  <ArrowRight size={16} />
                </button>
              </motion.div>
            ) : (
              <motion.form
                onSubmit={handleSubmit}
                className="space-y-5 mt-10"
                variants={formItems}
                initial="hidden"
                animate="show"
              >
                {invalid && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-3 p-4 border border-white/[0.06] rounded-xl bg-white/[0.02]"
                  >
                    <XCircle size={18} className="text-white/40 mt-0.5 shrink-0" />
                    <div className="text-sm text-white/50 leading-relaxed">
                      {error}
                      <Link href="/forgot-password" className="block mt-2 text-white/70 hover:text-white underline underline-offset-4 decoration-white/20">
                        Request a new link
                      </Link>
                    </div>
                  </motion.div>
                )}

                {!invalid && (
                  <>
                    <motion.div variants={formItem}>
                      <label htmlFor="reset-password" className="block text-[11px] text-white/25 mb-2 uppercase tracking-wider">
                        New password
                      </label>
                      <div className="relative">
                        <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
                        <input
                          id="reset-password"
                          type="password"
                          required
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="••••••••"
                          autoComplete="new-password"
                          minLength={8}
                          className="!pl-10"
                        />
                      </div>
                    </motion.div>
                    <motion.div variants={formItem}>
                      <label htmlFor="reset-confirm" className="block text-[11px] text-white/25 mb-2 uppercase tracking-wider">
                        Confirm password
                      </label>
                      <div className="relative">
                        <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
                        <input
                          id="reset-confirm"
                          type="password"
                          required
                          value={confirm}
                          onChange={(e) => setConfirm(e.target.value)}
                          placeholder="••••••••"
                          autoComplete="new-password"
                          minLength={8}
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
                      <button
                        type="submit"
                        disabled={isLoading}
                        className="btn-premium btn-glow w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : null}
                        Update password
                        {!isLoading && <ArrowRight size={16} />}
                      </button>
                    </motion.div>
                  </>
                )}
              </motion.form>
            )}
          </div>
        </AnimatedBorder>
      </motion.div>
    </div>
  );
}
