'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Loader2, MailCheck, XCircle } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import AnimatedBorder from '@/components/AnimatedBorder';
import MagneticButton from '@/components/MagneticButton';
import { apiPost } from '@/lib/api';

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailForm />
    </Suspense>
  );
}

type State = 'verifying' | 'success' | 'error';

function VerifyEmailForm() {
  const [state, setState] = useState<State>('verifying');
  const [message, setMessage] = useState('');
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setState('error');
      setMessage('This verification link is missing its token. Please request a new email.');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiPost<{ message: string; email: string }>('/api/auth/verify-email', { token });
        if (!cancelled) {
          setState('success');
          setMessage(res.email ? `${res.email} is now verified.` : 'Your email is now verified.');
        }
      } catch (err) {
        if (!cancelled) {
          setState('error');
          setMessage(err instanceof Error ? err.message : 'This link is invalid or has expired.');
        }
      }
    })();
    return () => { cancelled = true; };
  }, [searchParams]);

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
              <h1 className="text-4xl font-bold tracking-tight">
                {state === 'success' ? 'Email verified' : state === 'error' ? 'Verification failed' : 'Verifying…'}
              </h1>
            </motion.div>

            <motion.div
              variants={formItem}
              initial="hidden"
              animate="show"
              className="mt-10 space-y-5"
            >
              <div className="flex items-start gap-3 p-4 border border-white/[0.06] rounded-xl bg-white/[0.02]">
                {state === 'verifying' && (
                  <>
                    <Loader2 size={18} className="text-white/40 mt-0.5 shrink-0 animate-spin" />
                    <p className="text-sm text-white/50 leading-relaxed">
                      Checking your verification link…
                    </p>
                  </>
                )}
                {state === 'success' && (
                  <>
                    <MailCheck size={18} className="text-white/80 mt-0.5 shrink-0" />
                    <p className="text-sm text-white/50 leading-relaxed">
                      {message} Your account is fully activated.
                    </p>
                  </>
                )}
                {state === 'error' && (
                  <>
                    <XCircle size={18} className="text-white/60 mt-0.5 shrink-0" />
                    <p className="text-sm text-white/50 leading-relaxed">
                      {message} Links expire after 24 hours and can only be used once —
                      request a fresh email from your dashboard.
                    </p>
                  </>
                )}
              </div>

              {state !== 'verifying' && (
                <MagneticButton
                  onClick={() => router.push('/dashboard')}
                  className="btn-premium w-full bg-white text-black py-3.5 rounded-full font-semibold text-sm flex items-center justify-center gap-2"
                >
                  {state === 'success' ? 'Go to dashboard' : 'Back to dashboard'}
                  <ArrowRight size={16} />
                </MagneticButton>
              )}
            </motion.div>
          </div>
        </AnimatedBorder>
      </motion.div>
    </div>
  );
}
