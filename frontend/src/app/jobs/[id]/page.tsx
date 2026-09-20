'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet, apiPost, apiDelete, apiFetch } from '@/lib/store';
import { apiStream } from '@/lib/api';
import { formatINRRange } from '@/lib/format';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MapPin, Clock, IndianRupee, DollarSign, Briefcase, ArrowLeft, Bookmark, BookmarkCheck,
  ExternalLink, Loader2, AlertCircle, CheckCircle2, Sparkles, Brain, ChevronDown, Target
} from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import TiltCard from '@/components/TiltCard';
import AnimatedScoreRing from '@/components/AnimatedScoreRing';
import CompanyLogo from '@/components/CompanyLogo';
import ApplyModal from '@/components/ApplyModal';
import { useToast } from '@/components/Toast';

interface JobDetail {
  id: number | string;
  company_id: number;
  title: string;
  description: string;
  requirements: string;
  responsibilities: string;
  preferred_qualifications: string;
  skills_required: string;
  skills_preferred: string;
  location: string;
  work_type: string;
  salary_min: number;
  salary_max: number;
  experience_level: string;
  employment_type: string;
  application_url: string;
  posted_at: string;
  company_name: string;
  company_logo: string;
  company_industry: string;
  match_score: number;
  is_saved: boolean;
  is_applied: boolean;
}

function parseSkills(str: string): string[] {
  if (!str) return [];
  try { const p = JSON.parse(str); return Array.isArray(p) ? p : []; }
  catch { return str.split(',').map(s => s.trim()).filter(Boolean); }
}

function formatSalary(min: number, max: number, currency?: string, raw?: string): string {
  // Free-board jobs (Remotive/Jobicy): no structured salary → raw string;
  // structured but non-INR → $k format.
  if (!min && !max) return raw || '';
  if (currency && currency !== 'INR') {
    const fmt = (n: number) => `$${Math.round(n / 1000)}k`;
    if (min && max) return `${fmt(min)} – ${fmt(max)}`;
    if (min) return `From ${fmt(min)}`;
    return `Up to ${fmt(max!)}`;
  }
  return formatINRRange(min, max);
}

function MatchBreakdown({ matchData }: { matchData: any }) {
  if (!matchData) return null;

  const overall = Math.round(matchData.breakdown?.overall || 0);
  const isStrong = overall >= 80;

  const bars = [
    { label: 'Skills', value: matchData.breakdown?.skills || 0, icon: '⚡' },
    { label: 'Experience', value: matchData.breakdown?.experience || 0, icon: '📊' },
    { label: 'Role', value: matchData.breakdown?.role || 0, icon: '🎯' },
    { label: 'Location', value: matchData.breakdown?.location || 0, icon: '📍' },
    { label: 'Work Type', value: matchData.breakdown?.work_type || 0, icon: '🏠' },
    { label: 'Salary', value: matchData.breakdown?.salary || 0, icon: '💰' },
  ];

  return (
    <div className="space-y-6">
      {/* Overall score with animated ring */}
      <div className="text-center py-4">
        <div className="relative inline-flex items-center justify-center">
          <svg width="100" height="100" viewBox="0 0 100 100" className="transform -rotate-90">
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
            <motion.circle
              cx="50" cy="50" r="42" fill="none"
              stroke={isStrong ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.25)'}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 42}`}
              initial={{ strokeDashoffset: 2 * Math.PI * 42 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 42 * (1 - overall / 100) }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <p className="text-2xl font-bold">{overall}%</p>
            <p className="text-[9px] text-white/25 uppercase tracking-wider">Match</p>
          </div>
        </div>
        <p className="text-xs text-white/40 mt-2">
          {overall >= 80 ? 'Strong fit' : overall >= 60 ? 'Good fit' : 'Partial fit'}
        </p>
      </div>

      {/* Breakdown bars */}
      <div className="space-y-2.5">
        {bars.map((bar) => (
          <div key={bar.label}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-white/35 flex items-center gap-1.5">
                <span className="text-[10px]">{bar.icon}</span> {bar.label}
              </span>
              <span className="text-white/50 font-mono text-[11px]">{Math.round(bar.value)}%</span>
            </div>
            <div className="h-1 bg-white/[0.04] rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${bar.value}%` }}
                transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className={`h-full rounded-full ${bar.value >= 70 ? 'bg-white/50' : bar.value >= 40 ? 'bg-white/25' : 'bg-white/12'}`}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Strong matches */}
      {matchData.breakdown?.strong_matches?.length > 0 && (
        <div>
          <p className="text-[10px] text-white/25 mb-2 uppercase tracking-wider">Strong matches</p>
          <div className="flex flex-wrap gap-1.5">
            {matchData.breakdown.strong_matches.map((s: string) => (
              <span key={s} className="px-2.5 py-1 bg-white/[0.06] border border-white/[0.08] rounded-full text-xs text-white/60 flex items-center gap-1">
                <CheckCircle2 size={10} className="text-white/40" /> {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing skills */}
      {matchData.breakdown?.missing_skills?.length > 0 && (
        <div>
          <p className="text-[10px] text-white/25 mb-2 uppercase tracking-wider">Missing skills</p>
          <div className="flex flex-wrap gap-1.5">
            {matchData.breakdown.missing_skills.map((s: string) => (
              <span key={s} className="px-2.5 py-1 bg-white/[0.02] border border-white/[0.04] rounded-full text-xs text-white/30 flex items-center gap-1">
                <AlertCircle size={10} className="text-white/20" /> {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* AI Explanation */}
      {matchData.explanation && (
        <div className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl">
          <p className="text-[10px] text-white/25 mb-2 uppercase tracking-wider flex items-center gap-1.5">
            <Brain size={11} /> Why this matches you
          </p>
          <div className="text-xs text-white/45 leading-relaxed whitespace-pre-wrap">
            {matchData.explanation.replace(/\*\*/g, '')}
          </div>
        </div>
      )}
    </div>
  );
}

/** Render AI text: bold, bullets, numbered lines, paragraphs. No HTML. */
function AiAnswer({ text }: { text: string }) {
  const lines = text.replace(/\*\*/g, '').split('\n');
  return (
    <div className="text-xs text-white/50 leading-relaxed space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-1.5" />;
        if (/^[•\-*/]\s/.test(trimmed)) {
          return (
            <div key={i} className="flex items-start gap-2 ml-1">
              <span className="text-white/20 mt-1.5">•</span>
              <span className="text-white/55">{trimmed.replace(/^[•\-*/]\s/, '')}</span>
            </div>
          );
        }
        if (/^\d+[.)]\s/.test(trimmed)) {
          return (
            <div key={i} className="flex items-start gap-2 ml-1">
              <span className="text-white/30">{trimmed.match(/^\d+/)?.[0]}.</span>
              <span className="text-white/55">{trimmed.replace(/^\d+[.)]\s/, '')}</span>
            </div>
          );
        }
        return <p key={i} className="text-white/55">{trimmed}</p>;
      })}
    </div>
  );
}

interface AnswerThread {
  question: string;
  label: string;
  text: string;
  streaming: boolean;
}

const ACTIONS = [
  { key: 'why_match', label: 'Why am I a match?', icon: '🎯' },
  { key: 'missing', label: 'What am I missing?', icon: '🔍' },
  { key: 'apply_tips', label: 'How should I apply?', icon: '📝' },
  { key: 'tailor_resume', label: 'Tailor my resume', icon: '📄' },
  { key: 'prepare', label: 'Interview prep', icon: '🎤' },
] as const;

function AiActionPanel({ job, user }: { job: JobDetail; user: any }) {
  const [activeAction, setActiveAction] = useState('');
  const [answers, setAnswers] = useState<AnswerThread[]>([]);
  const [loadingAction, setLoadingAction] = useState('');

  const handleAiAction = async (action: string) => {
    if (!user || loadingAction) return;
    setActiveAction(action);
    setLoadingAction(action);

    const meta = ACTIONS.find(a => a.key === action)!;

    // Remove any previous answer for this question and append a streaming thread
    setAnswers(prev => [
      ...prev.filter(a => a.question !== action),
      { question: action, label: meta.label, text: '', streaming: true },
    ]);

    // Non-AI-user-facing note: the endpoint streams NDJSON tokens
    let streamErr = '';
    try {
      await apiStream('/api/ai/job-question/stream', { job_id: Number(job.id), question: action }, {
        onToken: (token) => {
          setAnswers(prev => prev.map(a =>
            a.question === action ? { ...a, text: a.text + token } : a
          ));
        },
        onDone: (final) => {
          const full = (final as any)?.full;
          setAnswers(prev => prev.map(a =>
            a.question === action
              ? { ...a, text: full || a.text || 'No response available.', streaming: false }
              : a
          ));
        },
      });
    } catch {
      streamErr = 'AI service is temporarily busy. Please try again in a moment.';
    }
    if (streamErr) {
      setAnswers(prev => prev.map(a =>
        a.question === action ? { ...a, text: streamErr, streaming: false } : a
      ));
    }
    setLoadingAction('');
  };

  const actions = ACTIONS;

  return (
    <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
        <Sparkles size={14} className="text-white/30" />
        AI Assistant
      </h3>
      <div className="space-y-1.5">
        {actions.map((action) => (
          <button
            key={action.key}
            onClick={() => handleAiAction(action.key)}
            disabled={!!loadingAction}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all duration-300 flex items-center gap-2 ${
              activeAction === action.key
                ? 'bg-white/[0.08] text-white border border-white/[0.08]'
                : 'text-white/35 hover:text-white/55 hover:bg-white/[0.03] border border-transparent'
            }`}
          >
            {loadingAction === action.key
              ? <Loader2 size={11} className="animate-spin shrink-0" />
              : <span className="text-[11px] shrink-0">{action.icon}</span>}
            {action.label}
          </button>
        ))}
      </div>

      {/* Answer threads — newest question first, each keeps its own answer */}
      <div className="mt-4 space-y-3">
        <AnimatePresence initial={false}>
          {[...answers].reverse().map((thread) => (
            <motion.div
              key={thread.question}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl"
            >
              <p className="text-[10px] text-white/20 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Sparkles size={10} /> {thread.label}
                {thread.streaming && <Loader2 size={10} className="animate-spin text-white/30" />}
              </p>
              {thread.text
                ? <AiAnswer text={thread.text} />
                : <p className="text-xs text-white/25 animate-pulse">Thinking…</p>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuthStore();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [matchData, setMatchData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [matchLoading, setMatchLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [saved, setSaved] = useState(false);
  const [applied, setApplied] = useState(false);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showDescription, setShowDescription] = useState(true);
  const { addToast } = useToast();

  const isJsearch = String(params.id).startsWith('jsearch_');

  useEffect(() => { loadJob(); }, [params.id]);

  const loadJob = async () => {
    try {
      const data = await apiGet<JobDetail>(`/api/jobs/${params.id}`);
      setJob(data);
      setSaved(data.is_saved || false);
      setApplied(data.is_applied || false);
      if (user && data.match_score > 0) loadMatchAnalysis();
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const loadMatchAnalysis = async () => {
    if (!user) return;
    setMatchLoading(true);
    try {
      // Pass the raw id — backend resolves both numeric (local) and
      // prefixed (jsearch_/remotive_/jobicy_) external jobs.
      const data = await apiPost<any>('/api/ai/match', { job_id: params.id });
      setMatchData(data);
    } catch (err) { console.error(err); }
    finally { setMatchLoading(false); }
  };

  const handleSave = async () => {
    if (!user) { router.push('/login'); return; }
    try {
      if (saved) {
        await apiDelete(`/api/jobs/${params.id}/save`);
        setSaved(false);
        addToast('Job unsaved', 'info');
      } else {
        await apiPost(`/api/jobs/${params.id}/save`);
        setSaved(true);
        addToast(`Saved "${job?.title}"`, 'success');
      }
    } catch {
      addToast('Failed to save job', 'error');
    }
  };

  const handleApply = async () => {
    if (!user) { router.push('/login'); return; }
    const externalUrl = job?.application_url || (job as any)?.google_link;
    if (externalUrl) {
      const win = window.open(externalUrl, '_blank', 'noopener,noreferrer');
      if (win) win.opener = null;
      addToast('Opening application page...', 'info');
      return;
    }
    setShowApplyModal(true);
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="skeleton h-4 w-24 mb-6 rounded" />
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-start gap-4">
              <div className="skeleton w-14 h-14 rounded-xl shrink-0" />
              <div className="space-y-3 flex-1">
                <div className="skeleton h-7 w-3/4 rounded" />
                <div className="skeleton h-4 w-1/2 rounded" />
                <div className="flex gap-3">
                  <div className="skeleton h-4 w-20 rounded" />
                  <div className="skeleton h-4 w-16 rounded" />
                  <div className="skeleton h-4 w-24 rounded" />
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="skeleton h-10 w-32 rounded-full" />
              <div className="skeleton h-10 w-24 rounded-full" />
            </div>
            <div className="space-y-4">
              <div className="skeleton h-5 w-32 rounded" />
              <div className="skeleton h-4 w-full rounded" />
              <div className="skeleton h-4 w-full rounded" />
              <div className="skeleton h-4 w-5/6 rounded" />
              <div className="skeleton h-4 w-full rounded" />
              <div className="skeleton h-4 w-2/3 rounded" />
            </div>
            <div className="space-y-4">
              <div className="skeleton h-5 w-28 rounded" />
              <div className="flex flex-wrap gap-2">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="skeleton h-7 w-20 rounded-lg" />
                ))}
              </div>
            </div>
          </div>
          <div className="space-y-5">
            <div className="skeleton h-48 rounded-xl" />
            <div className="skeleton h-64 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <p className="text-white/40">Job not found</p>
        <Link href="/jobs" className="text-sm text-white/30 hover:text-white/60 mt-4 inline-block">Back to jobs</Link>
      </div>
    );
  }

  const requiredSkills = parseSkills(job.skills_required);
  const preferredSkills = parseSkills(job.skills_preferred);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 relative">
      <FloatingOrbs count={2} className="opacity-15" />

      <div className="relative z-10">
        {/* Back button */}
        <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-white/25 hover:text-white/50 mb-6 transition-colors">
          <ArrowLeft size={14} /> Back to jobs
        </Link>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              {/* Header */}
              <div className="flex items-start gap-4 mb-6">
                <CompanyLogo src={job.company_logo} name={job.company_name || ''} size="lg" className="flex-shrink-0" />
                <div>
                  <h1 className="text-2xl md:text-3xl font-bold tracking-tight">{job.title}</h1>
                  <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-white/35">
                    <Link href={`/company/${job.company_id}`} className="hover:text-white/60 transition-colors">{job.company_name}</Link>
                    <span className="flex items-center gap-1"><MapPin size={13} />{job.location}</span>
                    <span className="capitalize">{job.work_type}</span>
                    <span className="flex items-center gap-1">{(job as any).salary_currency && (job as any).salary_currency !== 'INR' ? <DollarSign size={13} /> : <IndianRupee size={13} />}{formatSalary(job.salary_min, job.salary_max, (job as any).salary_currency, (job as any).salary_raw)}</span>
                    <span className="flex items-center gap-1 capitalize"><Briefcase size={13} />{job.experience_level}</span>
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3 mb-8 flex-wrap">
                {applied ? (
                  <span className="bg-white/[0.08] text-white/50 px-5 py-2.5 rounded-full text-sm font-medium flex items-center gap-2">
                    <CheckCircle2 size={14} /> Applied
                  </span>
                ) : (
                  <button onClick={handleApply} disabled={applying} className="btn-glow bg-white text-black px-6 py-2.5 rounded-full font-semibold text-sm flex items-center gap-2 hover:bg-white/90 transition-all disabled:opacity-50">
                    {applying ? <Loader2 size={14} className="animate-spin" /> : null}
                    {(job.application_url || (job as any).google_link) ? 'Apply Now' : 'Apply'}
                  </button>
                )}
                <button onClick={handleSave} className={`px-4 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 border transition-all duration-300 ${saved ? 'border-white/20 text-white bg-white/[0.04]' : 'border-white/[0.06] text-white/35 hover:text-white/55 hover:border-white/[0.15]'}`}>
                  {saved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                  {saved ? 'Saved' : 'Save'}
                </button>
                {((job as any).google_link || job.application_url) && (
                  <a href={(job as any).google_link || job.application_url} target="_blank" rel="noopener noreferrer" className="px-4 py-2.5 rounded-full text-sm text-white/35 hover:text-white/55 flex items-center gap-2 border border-white/[0.06] hover:border-white/[0.15] transition-all">
                    <ExternalLink size={14} /> {(job as any).publisher || 'View on Google'}
                  </a>
                )}
              </div>
            </motion.div>

            {/* Description */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="space-y-6">
              <Section title="About the role">
                <p className="whitespace-pre-line">{job.description}</p>
              </Section>

              {job.responsibilities && (
                <Section title="Responsibilities">
                  <p className="whitespace-pre-line">{job.responsibilities}</p>
                </Section>
              )}

              {job.requirements && (
                <Section title="Requirements">
                  <p className="whitespace-pre-line">{job.requirements}</p>
                </Section>
              )}

              {job.preferred_qualifications && (
                <Section title="Preferred qualifications">
                  <p className="whitespace-pre-line">{job.preferred_qualifications}</p>
                </Section>
              )}

              <Section title="Required skills">
                <div className="flex flex-wrap gap-2">
                  {requiredSkills.map((s) => (
                    <span key={s} className="px-3 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-sm text-white/55">{s}</span>
                  ))}
                </div>
              </Section>

              {preferredSkills.length > 0 && (
                <Section title="Nice to have">
                  <div className="flex flex-wrap gap-2">
                    {preferredSkills.map((s) => (
                      <span key={s} className="px-3 py-1 bg-white/[0.02] border border-white/[0.04] rounded-lg text-sm text-white/35">{s}</span>
                    ))}
                  </div>
                </Section>
              )}
            </motion.div>
          </div>

          {/* Sidebar */}
          <div className="space-y-5">
            {/* Match Score */}
            {user && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <TiltCard tiltAmount={3}>
                  <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                    <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                      <Target size={14} className="text-white/30" />
                      Your Match
                    </h3>
                    {matchLoading ? (
                      <div className="space-y-3">
                        <div className="skeleton h-24 rounded-lg" />
                        <div className="skeleton h-32 rounded-lg" />
                      </div>
                    ) : matchData ? (
                      <MatchBreakdown matchData={matchData} />
                    ) : (
                      <div className="flex flex-col items-center py-4">
                        <AnimatedScoreRing score={Math.round(job.match_score)} size={80} strokeWidth={4} />
                        <p className="text-xs text-white/25 mt-2">Match score</p>
                      </div>
                    )}
                  </div>
                </TiltCard>
              </motion.div>
            )}

            {/* AI Actions */}
            {user && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <AiActionPanel job={job} user={user} />
              </motion.div>
            )}

            {!user && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-[#050505] border border-white/[0.04] rounded-xl p-5 text-center">
                <p className="text-sm text-white/35 mb-3">Sign in to see your match analysis</p>
                <Link href="/login" className="text-xs text-white/45 hover:text-white/75 underline underline-offset-4 transition-colors">Sign in</Link>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {job && (
        <ApplyModal
          isOpen={showApplyModal}
          onClose={() => setShowApplyModal(false)}
          jobId={job.id}
          jobTitle={job.title}
          companyName={job.company_name}
          applicationUrl={job.application_url}
          onApplied={() => setApplied(true)}
        />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-white/50 mb-3 uppercase tracking-wider">{title}</h3>
      <div className="text-sm text-white/45 leading-relaxed">{children}</div>
    </div>
  );
}
