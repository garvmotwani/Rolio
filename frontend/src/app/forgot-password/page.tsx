'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2, Mail, CheckCircle2 } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import AnimatedBorder from '@/components/AnimatedBorder';
import MagneticButton from '@/components/MagneticButton';
import { apiPost } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || isLoading) return;
    setIsLoading(true);
    try {
      // Generic response either way — the UI mirrors that honesty
      await apiPost('/api/auth/forgot-password', { email });
    } catch {
      // Still show the sent state: the endpoint is generic by design
    } finally {
      setSent(true);
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
              <h1 className="text-4xl font-bold tracking-tight">Forgot password</h1>
              <p className="text-sm text-white/30 mt-3">
                {sent
                  ? "Check your inbox for the reset link."
                  : "Enter your email and we'll send you a reset link."}
              </p>
            </motion.div>

            {sent ? (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="mt-10 space-y-5"
              >
                <div className="flex items-start gap-3 p-4 border border-white/[0.06] rounded-xl bg-white/[0.02]">
                  <CheckCircle2 size={18} className="text-white/60 mt-0.5 shrink-0" />
                  <p className="text-sm text-white/50 leading-relaxed">
                    If an account exists for <span className="text-white/80">{email}</span>,
                    a reset link is on its way. It expires in 30 minutes.
                  </p>
                </div>
                <MagneticButton
                  onClick={() => router.push('/login')}
                  className="btn-premium w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2"
                >
                  Back to sign in
                  <ArrowRight size={16} />
                </MagneticButton>
                <p className="text-center text-xs text-white/20">
                  Didn&apos;t get it? Check your spam folder or{' '}
                  <button
                    type="button"
                    onClick={() => setSent(false)}
                    className="text-white/50 hover:text-white/80 transition-colors underline underline-offset-4 decoration-white/15 hover:decoration-white/40"
                  >
                    try again
                  </button>
                </p>
              </motion.div>
            ) : (
              <motion.form
                onSubmit={handleSubmit}
                className="space-y-5 mt-10"
                variants={formItems}
                initial="hidden"
                animate="show"
              >
                <motion.div variants={formItem}>
                  <label htmlFor="forgot-email" className="block text-[11px] text-white/25 mb-2 uppercase tracking-wider">
                    Email
                  </label>
                  <div className="relative">
                    <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
                    <input
                      id="forgot-email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      autoComplete="email"
                      className="!pl-10"
                    />
                  </div>
                </motion.div>

                <motion.div variants={formItem}>
                  <MagneticButton
                    type="submit"
                    disabled={isLoading || !email}
                    className="btn-premium btn-glow w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {isLoading ? <Loader2 size={16} className="animate-spin" /> : null}
                    Send reset link
                    {!isLoading && <ArrowRight size={16} />}
                  </MagneticButton>
                </motion.div>

                <motion.p variants={formItem} className="text-center text-sm text-white/20 mt-10">
                  Remembered it?{' '}
                  <Link href="/login" className="text-white/50 hover:text-white/80 transition-colors underline underline-offset-4 decoration-white/15 hover:decoration-white/40">
                    Sign in
                  </Link>
                </motion.p>
              </motion.form>
            )}
          </div>
        </AnimatedBorder>
      </motion.div>
    </div>
  );
}
