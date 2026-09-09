'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MailWarning, X, Loader2, Check } from 'lucide-react';
import { apiPost } from '@/lib/api';

/**
 * Slim banner shown on app pages while the signed-in user's email is
 * unverified. Offers a resend action (endpoint is enumeration-safe, so the
 * button simply confirms "link sent" either way).
 */
export default function VerifyEmailBanner({ email }: { email?: string }) {
  const [dismissed, setDismissed] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  if (dismissed) return null;

  const resend = async () => {
    if (sending || sent) return;
    setSending(true);
    try {
      await apiPost('/api/auth/send-verification');
      setSent(true);
    } catch {
      // Endpoint is generic; a failure still means try later
      setSent(true);
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="mb-6 flex items-center gap-3 bg-[#0a0a0a] border border-white/[0.07] rounded-xl px-4 py-3"
        role="status"
      >
        <MailWarning size={15} className="text-white/40 shrink-0" />
        <p className="text-[13px] text-white/45 flex-1 leading-snug">
          {sent ? (
            <>Verification link sent{email ? ' to ' : ''}{email ? <span className="text-white/70">{email}</span> : ''} — check your inbox{email ? '' : ' spam folder'} too.</>
          ) : (
            <>Please verify your email address to fully activate your account.</>
          )}
        </p>
        {!sent && (
          <button
            type="button"
            onClick={resend}
            disabled={sending}
            className="text-[12px] font-medium text-white/70 hover:text-white bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] rounded-full px-3.5 py-1.5 transition-all flex items-center gap-1.5 disabled:opacity-50 shrink-0"
          >
            {sending ? <Loader2 size={12} className="animate-spin" /> : null}
            {sending ? 'Sending…' : 'Resend link'}
          </button>
        )}
        {sent && (
          <span className="text-[12px] text-white/40 flex items-center gap-1.5 shrink-0">
            <Check size={12} />
            Sent
          </span>
        )}
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="text-white/20 hover:text-white/50 transition-colors shrink-0"
        >
          <X size={14} />
        </button>
      </motion.div>
    </AnimatePresence>
  );
}
