'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet, apiPost } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail, CheckCircle2, AlertCircle, RefreshCw, Unplug, ArrowRight,
  Loader2, Inbox, Link2, Clock, Search, ChevronRight, Zap,
  Shield, ExternalLink, Settings2
} from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import TiltCard from '@/components/TiltCard';

interface GmailStatus {
  connected: boolean;
  gmail_address: string;
  total_emails: number;
  matched_emails: number;
  last_sync: string | null;
  last_sync_status: string | null;
  emails_fetched_last_sync: number;
}

interface SyncResult {
  message: string;
  emails_fetched: number;
  new_emails: number;
  matched_emails: number;
}

export default function SettingsPageWrapper() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto px-6 py-10"><div className="skeleton h-10 w-48" /></div>}>
      <SettingsPage />
    </Suspense>
  );
}

function SettingsPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadGmailStatus();
  }, [user, hydrated, router]);

  // Handle OAuth callback — tokens are stored server-side now
  useEffect(() => {
    const gmailParam = searchParams.get('gmail');
    if (gmailParam === 'connected') {
      loadGmailStatus();
      // Clean URL
      window.history.replaceState({}, '', '/settings');
    } else if (gmailParam === 'error') {
      window.history.replaceState({}, '', '/settings');
    }
  }, [searchParams]);

  const loadGmailStatus = async () => {
    try {
      const data = await apiGet<GmailStatus>('/api/gmail/status');
      setGmailStatus(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const data = await apiGet<{ auth_url: string }>('/api/gmail/auth-url');
      window.location.href = data.auth_url;
    } catch (err: any) {
      alert(err.message || 'Failed to get auth URL');
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Disconnect Gmail? This will stop email syncing.')) return;
    try {
      await apiPost('/api/gmail/disconnect');
      setGmailStatus(null);
      loadGmailStatus();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await apiPost<SyncResult>('/api/gmail/sync');
      setSyncResult(result);
      loadGmailStatus();
    } catch (err: any) {
      alert(err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="space-y-6">
          <div className="skeleton h-10 w-48" />
          <div className="skeleton h-48 rounded-xl" />
          <div className="skeleton h-32 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-10" />

      <div className="relative z-10">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <Settings2 size={24} className="text-white/40" />
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Settings</h1>
          </div>
          <p className="text-white/30 text-sm">Manage your account and integrations</p>
        </motion.div>

        {/* Gmail Integration Card */}
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <TiltCard>
            <div className="bg-[#050505] border border-white/[0.04] rounded-2xl overflow-hidden">
              {/* Card header */}
              <div className="px-6 py-5 border-b border-white/[0.04]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                      gmailStatus?.connected ? 'bg-white/[0.08]' : 'bg-white/[0.03]'
                    }`}>
                      <Mail size={20} className={gmailStatus?.connected ? 'text-white/70' : 'text-white/25'} />
                    </div>
                    <div>
                      <h2 className="text-base font-semibold">Gmail Auto-Sync</h2>
                      <p className="text-xs text-white/30 mt-0.5">
                        {gmailStatus?.connected
                          ? `Connected to ${gmailStatus.gmail_address}`
                          : 'Connect Gmail to auto-track applications'
                        }
                      </p>
                    </div>
                  </div>
                  {gmailStatus?.connected ? (
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1.5 text-xs text-green-400/80 bg-green-400/10 px-2.5 py-1 rounded-full">
                        <CheckCircle2 size={12} />
                        Connected
                      </span>
                    </div>
                  ) : (
                    <button
                      onClick={handleConnect}
                      disabled={connecting}
                      className="btn-premium bg-white text-black px-4 py-2 rounded-full text-xs font-medium flex items-center gap-2 disabled:opacity-50"
                    >
                      {connecting ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />}
                      {connecting ? 'Connecting...' : 'Connect Gmail'}
                    </button>
                  )}
                </div>
              </div>

              {/* Connected state */}
              {gmailStatus?.connected && (
                <div className="px-6 py-5">
                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3 mb-5">
                    <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 text-center">
                      <p className="text-xl font-bold">{gmailStatus.total_emails}</p>
                      <p className="text-[10px] text-white/30 uppercase tracking-wider mt-1">Emails synced</p>
                    </div>
                    <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 text-center">
                      <p className="text-xl font-bold text-green-400/80">{gmailStatus.matched_emails}</p>
                      <p className="text-[10px] text-white/30 uppercase tracking-wider mt-1">Matched</p>
                    </div>
                    <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3 text-center">
                      <p className="text-xl font-bold">
                        {gmailStatus.last_sync
                          ? new Date(gmailStatus.last_sync).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                          : '—'
                        }
                      </p>
                      <p className="text-[10px] text-white/30 uppercase tracking-wider mt-1">Last sync</p>
                    </div>
                  </div>

                  {/* Sync button */}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleSync}
                      disabled={syncing}
                      className="flex-1 bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.08] rounded-xl py-3 text-sm font-medium flex items-center justify-center gap-2 transition-all disabled:opacity-50"
                    >
                      {syncing ? (
                        <>
                          <Loader2 size={16} className="animate-spin" />
                          Syncing emails...
                        </>
                      ) : (
                        <>
                          <RefreshCw size={16} />
                          Sync now
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleDisconnect}
                      className="px-4 py-3 rounded-xl border border-white/[0.04] text-white/25 hover:text-red-400/80 hover:border-red-400/20 transition-all"
                      title="Disconnect Gmail"
                    >
                      <Unplug size={16} />
                    </button>
                  </div>

                  {/* Sync result */}
                  <AnimatePresence>
                    {syncResult && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-4 overflow-hidden"
                      >
                        <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <CheckCircle2 size={14} className="text-green-400/80" />
                            <span className="text-xs font-medium text-green-400/80">Sync complete</span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div>
                              <p className="text-lg font-bold">{syncResult.emails_fetched}</p>
                              <p className="text-[10px] text-white/25">Fetched</p>
                            </div>
                            <div>
                              <p className="text-lg font-bold">{syncResult.new_emails}</p>
                              <p className="text-[10px] text-white/25">New</p>
                            </div>
                            <div>
                              <p className="text-lg font-bold text-green-400/80">{syncResult.matched_emails}</p>
                              <p className="text-[10px] text-white/25">Matched</p>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}

              {/* Disconnected state — feature explanation */}
              {!gmailStatus?.connected && (
                <div className="px-6 py-5">
                  <div className="space-y-3">
                    <FeatureItem
                      icon={<Inbox size={14} />}
                      title="Auto-detect applications"
                      description="Scans incoming emails to find job application confirmations"
                    />
                    <FeatureItem
                      icon={<Zap size={14} />}
                      title="Smart status updates"
                      description="Automatically updates application status from interview invites, rejections, and offers"
                    />
                    <FeatureItem
                      icon={<Shield size={14} />}
                      title="Read-only access"
                      description="We can only read your emails — we never send or modify anything"
                    />
                    <FeatureItem
                      icon={<Clock size={14} />}
                      title="Follow-up reminders"
                      description="Get reminders when you haven't heard back in a while"
                    />
                  </div>
                </div>
              )}
            </div>
          </TiltCard>
        </motion.div>

        {/* How it works */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-8"
        >
          <div className="bg-[#050505] border border-white/[0.04] rounded-2xl p-6">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Search size={14} className="text-white/30" />
              How email sync works
            </h3>
            <div className="space-y-4">
              {[
                { step: '1', text: 'Connect your Gmail with read-only access' },
                { step: '2', text: 'We scan the last 30 days of job-related emails from ATS platforms (Greenhouse, Lever, Workday, etc.)' },
                { step: '3', text: 'Emails are matched to your applications by company name, sender domain, and keywords' },
                { step: '4', text: 'Interview invites, rejections, and offers auto-update your application status' },
                { step: '5', text: 'All email data stays on your device — nothing is sent to external servers' },
              ].map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-[10px] font-mono text-white/40">{item.step}</span>
                  </div>
                  <p className="text-xs text-white/40 leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Application Tracking Features */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8"
        >
          <div className="bg-[#050505] border border-white/[0.04] rounded-2xl p-6">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Link2 size={14} className="text-white/30" />
              Application Tracking
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <TrackingFeature
                title="Timeline"
                description="Every status change, email, and note is logged in a chronological timeline"
              />
              <TrackingFeature
                title="Auto-status"
                description="Email content is analyzed to automatically update application stages"
              />
              <TrackingFeature
                title="Email linking"
                description="Correspondence is matched and linked to the correct application"
              />
              <TrackingFeature
                title="Follow-up reminders"
                description="Set reminders to follow up and never lose track of opportunities"
              />
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0 text-white/30">
        {icon}
      </div>
      <div>
        <p className="text-xs font-medium text-white/60">{title}</p>
        <p className="text-[11px] text-white/25 mt-0.5 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function TrackingFeature({ title, description }: { title: string; description: string }) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-3">
      <p className="text-xs font-medium text-white/50">{title}</p>
      <p className="text-[11px] text-white/25 mt-1 leading-relaxed">{description}</p>
    </div>
  );
}
