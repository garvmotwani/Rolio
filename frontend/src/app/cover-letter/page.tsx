'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, apiGet, apiPost } from '@/lib/store';
import { apiStream } from '@/lib/api';
import Link from 'next/link';
import {
  FileText, Sparkles, Copy, Check, ArrowRight,
  Briefcase, Loader2, RefreshCw
} from 'lucide-react';

export default function CoverLetterPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#050505] flex items-center justify-center"><Loader2 className="animate-spin text-white/40" size={24} /></div>}>
      <CoverLetterPage />
    </Suspense>
  );
}

function CoverLetterPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');

  const [applications, setApplications] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [tone, setTone] = useState('professional');
  const [length, setLength] = useState('medium');
  const [letter, setLetter] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [streamingText, setStreamingText] = useState('');

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadApplications();
  }, [user, hydrated, router]);

  const loadApplications = async () => {
    try {
      const apps = await apiGet<any[]>('/api/applications');
      setApplications(apps);
      if (jobId) {
        const match = apps.find(a => a.job_id === parseInt(jobId));
        if (match) setSelectedJob(match);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setFetching(false);
    }
  };

  const generate = async () => {
    if (!selectedJob || loading) return;
    setLoading(true);
    setLetter('');
    setStreamingText('');

    try {
      let finalLetter = '';
      await apiStream('/api/cover-letter/generate/stream', { job_id: selectedJob.job_id, tone, length }, {
        onToken: (token) => setStreamingText(prev => prev + token),
        onDone: (final) => {
          const payload = final as { letter?: string };
          finalLetter = payload?.letter || '';
          setLetter(finalLetter);
          setStreamingText('');
        },
      });
    } catch (err) {
      // Fallback to non-streaming
      try {
        const result = await apiPost<{ letter: string }>('/api/cover-letter/generate', {
          job_id: selectedJob.job_id, tone, length,
        });
        setLetter(result.letter);
      } catch {
        setLetter('Error generating cover letter. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!hydrated || !user) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <FileText size={18} className="text-white/40" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Cover Letter Generator</h1>
            <p className="text-white/25 text-sm">AI-tailored letters for each application</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Controls */}
          <div className="space-y-4">
            {/* Job Selection */}
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-[13px] font-semibold mb-3">Select Application</h3>
              {fetching ? (
                <div className="skeleton h-10 rounded-lg" />
              ) : applications.length === 0 ? (
                <div className="text-center py-6">
                  <p className="text-xs text-white/25">No applications yet</p>
                  <Link href="/jobs" className="text-xs text-white/40 hover:text-white/60 mt-2 inline-flex items-center gap-1">
                    Find jobs <ArrowRight size={10} />
                  </Link>
                </div>
              ) : (
                <select
                  value={selectedJob?.job_id || ''}
                  onChange={(e) => {
                    const app = applications.find(a => a.job_id === parseInt(e.target.value));
                    setSelectedJob(app || null);
                  }}
                  className="w-full bg-[#0a0a0a] border border-white/[0.06] rounded-lg px-3 py-2.5 text-sm text-white/70 outline-none focus:border-white/[0.12] transition-colors appearance-none cursor-pointer"
                >
                  <option value="">Choose a job...</option>
                  {applications.map(app => (
                    <option key={app.job_id} value={app.job_id}>
                      {app.job_title} @ {app.company_name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Tone */}
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-[13px] font-semibold mb-3">Tone</h3>
              <div className="space-y-2">
                {[
                  { value: 'professional', label: 'Professional', desc: 'Formal and confident' },
                  { value: 'enthusiastic', label: 'Enthusiastic', desc: 'Passionate and eager' },
                  { value: 'casual', label: 'Casual', desc: 'Friendly and conversational' },
                ].map(t => (
                  <button
                    key={t.value}
                    onClick={() => setTone(t.value)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                      tone === t.value
                        ? 'bg-white/[0.06] border-white/[0.12]'
                        : 'bg-transparent border-white/[0.04] hover:border-white/[0.08]'
                    }`}
                  >
                    <p className="text-sm font-medium text-white/70">{t.label}</p>
                    <p className="text-[11px] text-white/25 mt-0.5">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Length */}
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-[13px] font-semibold mb-3">Length</h3>
              <div className="space-y-2">
                {[
                  { value: 'short', label: 'Short', desc: '150-200 words' },
                  { value: 'medium', label: 'Medium', desc: '250-350 words' },
                  { value: 'long', label: 'Long', desc: '400-500 words' },
                ].map(l => (
                  <button
                    key={l.value}
                    onClick={() => setLength(l.value)}
                    className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                      length === l.value
                        ? 'bg-white/[0.06] border-white/[0.12]'
                        : 'bg-transparent border-white/[0.04] hover:border-white/[0.08]'
                    }`}
                  >
                    <p className="text-sm font-medium text-white/70">{l.label}</p>
                    <p className="text-[11px] text-white/25 mt-0.5">{l.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={generate}
              disabled={!selectedJob || loading}
              className="w-full bg-white text-black py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 hover:bg-white/90 transition-colors disabled:opacity-30 disabled:cursor-not-allowed press-scale"
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" /> Generating...</>
              ) : (
                <><Sparkles size={16} /> Generate Cover Letter</>
              )}
            </button>
          </div>

          {/* Output */}
          <div className="lg:col-span-2">
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl min-h-[500px]">
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.04]">
                <h3 className="text-[13px] font-semibold">Generated Letter</h3>
                {letter && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={generate}
                      className="p-1.5 rounded-lg hover:bg-white/[0.05] transition-colors"
                      title="Regenerate"
                    >
                      <RefreshCw size={14} className="text-white/30" />
                    </button>
                    <button
                      onClick={copyToClipboard}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] transition-colors text-xs text-white/50"
                    >
                      {copied ? <Check size={12} /> : <Copy size={12} />}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                )}
              </div>
              <div className="p-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 size={24} className="text-white/20 animate-spin mb-4" />
                    <p className="text-sm text-white/30 mb-4">Crafting your cover letter...</p>
                    {streamingText && (
                      <div className="w-full max-w-lg">
                        <div className="text-sm text-white/50 font-serif leading-relaxed whitespace-pre-wrap">
                          {streamingText}
                          <span className="animate-pulse text-white/30">|</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : letter && !loading ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="prose prose-invert max-w-none"
                  >
                    <div className="text-sm text-white/60 leading-relaxed whitespace-pre-wrap font-serif">
                      {letter}
                    </div>
                  </motion.div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <FileText size={32} className="text-white/10 mb-4" />
                    <p className="text-sm text-white/25">Select a job and click generate</p>
                    <p className="text-xs text-white/15 mt-1">Your letter will appear here</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
