'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet, apiPost, apiFetch } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, Download, Sparkles, ArrowLeft, Loader2, Briefcase,
  GraduationCap, Code, Target, RefreshCw, Copy, Check, ChevronDown
} from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import TiltCard from '@/components/TiltCard';

interface ResumeData {
  summary: string;
  contact?: { location?: string; email?: string; phone?: string };
  experience: Array<{ company: string; title: string; start?: string; end?: string; bullets: string[] }>;
  education: Array<{ institution: string; degree: string; field: string; year: string }>;
  skills: string[];
}

interface Job {
  id: number;
  title: string;
  company_name: string;
  skills_required: string;
}

export default function ResumeBuilderPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [resume, setResume] = useState<ResumeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'edit'>('preview');
  const [provider, setProvider] = useState('');

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadJobs();
  }, [user, hydrated, router]);

  const loadJobs = async () => {
    try {
      const data = await apiGet<{ jobs: Job[] }>('/api/jobs?limit=20');
      setJobs(data.jobs || []);
    } catch {}
  };

  const generateResume = async () => {
    setLoading(true);
    try {
      const result = await apiPost<{ resume: ResumeData; provider: string; tailored_for: string | null }>(
        '/api/resume-builder/generate',
        { job_id: selectedJob }
      );
      setResume(result.resume);
      setProvider(result.provider);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!resume) return;
    const text = formatResumeText(resume);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatResumeText = (r: ResumeData): string => {
    let text = '';
    if (user) {
      text += `${user.name?.toUpperCase()}\n`;
      const contact = [
        r.contact?.location || (user as any).location,
        (user as any).email,
        r.contact?.phone,
      ].filter(Boolean).join(' | ');
      if (contact) text += `${contact}\n`;
      text += '\n';
    }
    if (r.summary) text += `PROFESSIONAL SUMMARY\n${r.summary}\n\n`;
    if (r.experience?.length) {
      text += 'EXPERIENCE\n';
      r.experience.forEach(e => {
        const dates = [e.start, e.end].filter(Boolean).join(' – ');
        text += `${e.title} — ${e.company}${dates ? ` (${dates})` : ''}\n`;
        e.bullets.forEach(b => text += `  • ${b}\n`);
        text += '\n';
      });
    }
    if (r.education?.length) {
      text += 'EDUCATION\n';
      r.education.forEach(e => {
        text += `${e.degree}${e.field ? ' in ' + e.field : ''} — ${e.institution}${e.year ? ' (' + e.year + ')' : ''}\n`;
      });
      text += '\n';
    }
    if (r.skills?.length) {
      text += `SKILLS\n${r.skills.join(' · ')}\n`;
    }
    return text;
  };

  if (!hydrated || !user) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-4">
          <div className="skeleton h-8 w-48" />
          <div className="skeleton h-60 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 relative">
      <FloatingOrbs count={2} className="opacity-15" />

      <div className="relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Link href="/profile" className="inline-flex items-center gap-1.5 text-sm text-white/25 hover:text-white/50 mb-4 transition-colors">
            <ArrowLeft size={14} /> Back to profile
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">AI Resume Builder</h1>
          <p className="text-white/30 mt-2">
            Generate a tailored, ATS-friendly resume using AI
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Controls */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
            {/* Job selection */}
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Target size={14} className="text-white/30" />
                Tailor for job
              </h3>
              <p className="text-xs text-white/25 mb-3">
                Optionally select a job to tailor your resume
              </p>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                <button
                  onClick={() => setSelectedJob(null)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all ${
                    selectedJob === null
                      ? 'bg-white/[0.08] text-white border border-white/[0.1]'
                      : 'text-white/35 hover:text-white/55 hover:bg-white/[0.03] border border-transparent'
                  }`}
                >
                  General resume
                </button>
                {jobs.map(job => (
                  <button
                    key={job.id}
                    onClick={() => setSelectedJob(job.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all ${
                      selectedJob === job.id
                        ? 'bg-white/[0.08] text-white border border-white/[0.1]'
                        : 'text-white/35 hover:text-white/55 hover:bg-white/[0.03] border border-transparent'
                    }`}
                  >
                    <span className="font-medium">{job.title}</span>
                    <span className="text-white/20 ml-1.5">@ {job.company_name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Generate button */}
            <button
              onClick={generateResume}
              disabled={loading}
              className="w-full bg-white text-black py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 hover:bg-white/90 transition-all disabled:opacity-50 shadow-[0_0_24px_rgba(255,255,255,0.04)]"
            >
              {loading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Sparkles size={16} />
              )}
              {loading ? 'Generating...' : 'Generate Resume'}
            </button>

            {/* Actions */}
            {resume && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
              >
                <button
                  onClick={copyToClipboard}
                  className="w-full px-4 py-2.5 rounded-xl text-xs text-white/40 hover:text-white/60 border border-white/[0.06] hover:border-white/[0.12] flex items-center justify-center gap-2 transition-all"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? 'Copied!' : 'Copy to clipboard'}
                </button>
                <button
                  onClick={generateResume}
                  className="w-full px-4 py-2.5 rounded-xl text-xs text-white/40 hover:text-white/60 border border-white/[0.06] hover:border-white/[0.12] flex items-center justify-center gap-2 transition-all"
                >
                  <RefreshCw size={14} />
                  Regenerate
                </button>
                {provider && (
                  <p className="text-[10px] text-white/15 text-center">
                    Generated by {provider}
                  </p>
                )}
              </motion.div>
            )}
          </motion.div>

          {/* Resume preview */}
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-2"
          >
            {resume ? (
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl overflow-hidden">
                {/* Tab bar */}
                <div className="flex border-b border-white/[0.04]">
                  <button
                    onClick={() => setActiveTab('preview')}
                    className={`px-5 py-3 text-xs font-medium transition-colors ${
                      activeTab === 'preview' ? 'text-white border-b border-white' : 'text-white/30 hover:text-white/50'
                    }`}
                  >
                    Preview
                  </button>
                  <button
                    onClick={() => setActiveTab('edit')}
                    className={`px-5 py-3 text-xs font-medium transition-colors ${
                      activeTab === 'edit' ? 'text-white border-b border-white' : 'text-white/30 hover:text-white/50'
                    }`}
                  >
                    Raw text
                  </button>
                </div>

                <div className="p-8">
                  {activeTab === 'preview' ? (
                    <div className="space-y-8">
                      {/* Name + contact header */}
                      <div className="text-center pb-6 border-b border-white/[0.06]">
                        <h2 className="text-xl font-bold tracking-tight text-white/90">{user?.name}</h2>
                        <p className="text-xs text-white/30 mt-1">
                          {[
                            resume.contact?.location || (user as any)?.location,
                            (user as any)?.email,
                            resume.contact?.phone,
                          ].filter(Boolean).join('  ·  ')}
                        </p>
                      </div>

                      {/* Summary */}
                      {resume.summary && (
                        <section>
                          <h3 className="text-[11px] text-white/25 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <FileText size={12} /> Professional Summary
                          </h3>
                          <p className="text-sm text-white/60 leading-relaxed">{resume.summary}</p>
                        </section>
                      )}

                      {/* Experience */}
                      {resume.experience?.length > 0 && (
                        <section>
                          <h3 className="text-[11px] text-white/25 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <Briefcase size={12} /> Experience
                          </h3>
                          <div className="space-y-5">
                            {resume.experience.map((exp, i) => (
                              <div key={i}>
                                <div className="flex items-baseline gap-2 mb-2">
                                  <span className="text-sm font-semibold text-white/80">{exp.title}</span>
                                  <span className="text-xs text-white/30">— {exp.company}</span>
                                  {(exp.start || exp.end) && (
                                    <span className="text-[10px] text-white/20 ml-auto">
                                      {[exp.start, exp.end].filter(Boolean).join(' – ')}
                                    </span>
                                  )}
                                </div>
                                <ul className="space-y-1.5 ml-1">
                                  {exp.bullets.map((bullet, j) => (
                                    <li key={j} className="text-xs text-white/45 leading-relaxed flex items-start gap-2">
                                      <span className="text-white/15 mt-1.5">•</span>
                                      {bullet}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Education */}
                      {resume.education?.length > 0 && (
                        <section>
                          <h3 className="text-[11px] text-white/25 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <GraduationCap size={12} /> Education
                          </h3>
                          <div className="space-y-2">
                            {resume.education.map((edu, i) => (
                              <div key={i} className="flex items-baseline gap-2">
                                <span className="text-sm text-white/70 font-medium">{edu.degree}</span>
                                {edu.field && <span className="text-xs text-white/35">in {edu.field}</span>}
                                <span className="text-xs text-white/25">— {edu.institution}</span>
                                {edu.year && <span className="text-xs text-white/15 ml-auto">{edu.year}</span>}
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* Skills */}
                      {resume.skills?.length > 0 && (
                        <section>
                          <h3 className="text-[11px] text-white/25 uppercase tracking-wider mb-3 flex items-center gap-2">
                            <Code size={12} /> Skills
                          </h3>
                          <div className="flex flex-wrap gap-1.5">
                            {resume.skills.map((skill, i) => (
                              <span key={i} className="px-2.5 py-1 bg-white/[0.04] border border-white/[0.06] rounded-lg text-xs text-white/55">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </section>
                      )}
                    </div>
                  ) : (
                    <pre className="text-xs text-white/50 leading-relaxed whitespace-pre-wrap font-mono">
                      {formatResumeText(resume)}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-16 text-center">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mx-auto mb-5">
                  <FileText size={28} className="text-white/15" />
                </div>
                <h3 className="text-base font-semibold mb-2">No resume generated yet</h3>
                <p className="text-sm text-white/30 max-w-sm mx-auto">
                  Click &ldquo;Generate Resume&rdquo; to create an AI-tailored, ATS-friendly resume from your profile
                </p>
                <div className="flex items-center justify-center gap-3 mt-6 text-xs text-white/20">
                  <span className="flex items-center gap-1"><Sparkles size={12} /> AI-powered</span>
                  <span>•</span>
                  <span className="flex items-center gap-1"><Target size={12} /> Job-tailored</span>
                  <span>•</span>
                  <span className="flex items-center gap-1"><FileText size={12} /> ATS-optimized</span>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
