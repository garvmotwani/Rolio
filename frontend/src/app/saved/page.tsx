'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet, apiDelete } from '@/lib/store';
import { formatINR } from '@/lib/format';
import { apiDownload } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Bookmark, MapPin, Clock, ArrowRight, Trash2, Download, IndianRupee } from 'lucide-react';
import TiltCard from '@/components/TiltCard';
import FloatingOrbs from '@/components/FloatingOrbs';
import CompanyLogo from '@/components/CompanyLogo';

interface SavedJob {
  id: number;
  job_id: number;
  saved_at: string;
  job_title: string;
  company_name: string;
  company_logo: string;
  job_location: string;
  job_work_type: string;
  job_salary_min: number;
  job_salary_max: number;
  skills_required: string;
  match_score: number;
  is_applied: boolean;
}

function parseSkills(str: string): string[] {
  if (!str) return [];
  try { const p = JSON.parse(str); return Array.isArray(p) ? p : []; }
  catch { return str.split(',').map(s => s.trim()).filter(Boolean); }
}

export default function SavedJobsPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadSaved();
  }, [user, hydrated, router]);

  const loadSaved = async () => {
    try {
      const data = await apiGet<SavedJob[]>('/api/saved-jobs');
      setSavedJobs(data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleUnsave = async (jobId: number) => {
    setRemovingId(jobId);
    // Delay removal for animation
    setTimeout(async () => {
      try {
        await apiDelete(`/api/jobs/${jobId}/save`);
        setSavedJobs(savedJobs.filter((j) => j.job_id !== jobId));
        setRemovingId(null);
      } catch { setRemovingId(null); }
    }, 300);
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-15" />

      <div className="relative z-10">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Saved Jobs</h1>
              <p className="text-white/30 text-sm mt-1">{savedJobs.length} saved opportunit{savedJobs.length === 1 ? 'y' : 'ies'}</p>
            </div>
            {savedJobs.length > 0 && (
              <button
                onClick={async () => {
                  setExporting(true);
                  try {
                    await apiDownload(
                      '/api/export/saved-jobs',
                      `saved-jobs-${new Date().toISOString().split('T')[0]}.csv`
                    );
                  } catch (err) {
                    console.error('Export failed:', err);
                  } finally {
                    setExporting(false);
                  }
                }}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.06] transition-all disabled:opacity-50"
              >
                <Download size={12} className={exporting ? 'animate-bounce' : ''} />
                {exporting ? 'Exporting...' : 'Export CSV'}
              </button>
            )}
          </div>
        </motion.div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="skeleton h-28 rounded-xl" />)}
          </div>
        ) : savedJobs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-24"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mx-auto mb-5">
              <Bookmark size={28} className="text-white/10" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Nothing saved yet</h3>
            <p className="text-white/25 text-sm max-w-sm mx-auto leading-relaxed mb-6">
              Save jobs you&apos;re interested in and they&apos;ll appear here for quick access.
            </p>
            <Link
              href="/jobs"
              className="inline-flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-full text-sm font-medium hover:bg-white/90 transition-all"
            >
              Browse jobs <ArrowRight size={14} />
            </Link>
          </motion.div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {savedJobs.map((job, i) => {
                const skills = parseSkills(job.skills_required);
                const score = job.match_score ? Math.round(job.match_score) : null;
                const isRemoving = removingId === job.job_id;

                return (
                  <motion.div
                    key={job.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{
                      opacity: isRemoving ? 0 : 1,
                      y: isRemoving ? -10 : 0,
                      scale: isRemoving ? 0.98 : 1,
                      filter: isRemoving ? 'blur(4px)' : 'blur(0px)',
                    }}
                    exit={{ opacity: 0, x: -20, transition: { duration: 0.2 } }}
                    transition={{ delay: i * 0.03, duration: 0.4 }}
                  >
                    <TiltCard tiltAmount={2}>
                      <div className="section-card p-5 hover:border-white/[0.08] transition-all duration-500 relative overflow-hidden group">
                        {/* Hover glow */}
                        <div className="absolute -top-16 -right-16 w-32 h-32 bg-white/[0.015] rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

                        <div className="relative z-10 flex items-start justify-between gap-4">
                          <Link href={`/jobs/${job.job_id}`} className="flex items-start gap-3 flex-1 min-w-0 group/link">
                            <CompanyLogo src={job.company_logo} name={job.company_name || ''} size="md" className="flex-shrink-0 group-hover:border-white/[0.1] transition-colors duration-500" />
                            <div>
                              <h3 className="font-semibold text-sm group-hover/link:text-white transition-colors">{job.job_title}</h3>
                              <p className="text-xs text-white/30 mt-0.5">{job.company_name}</p>
                              <div className="flex items-center gap-3 mt-1.5 text-xs text-white/25 flex-wrap">
                                <span className="flex items-center gap-1"><MapPin size={11} />{job.job_location}</span>
                                <span className="capitalize">{job.job_work_type}</span>
                                {job.job_salary_min > 0 && (
                                  <span><IndianRupee size={11} className="inline" /> {formatINR(job.job_salary_min)} – {formatINR(job.job_salary_max)}</span>
                                )}
                              </div>
                              {skills.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mt-2">
                                  {skills.slice(0, 4).map((s) => (
                                    <span key={s} className="px-2 py-0.5 bg-white/[0.03] border border-white/[0.03] rounded text-xs text-white/35">{s}</span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </Link>
                          <div className="flex flex-col items-end gap-2 flex-shrink-0">
                            {score !== null && (
                              <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                                score >= 80 ? 'bg-white/10 text-white' : 'bg-white/[0.04] text-white/50'
                              }`}>
                                {score}%
                              </span>
                            )}
                            {job.is_applied && (
                              <span className="text-[11px] text-white/25 bg-white/[0.03] px-2 py-0.5 rounded-full">Applied</span>
                            )}
                            <button
                              onClick={() => handleUnsave(job.job_id)}
                              className="p-1.5 text-white/15 hover:text-red-400 transition-colors rounded-lg hover:bg-white/[0.03]"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      </div>
                    </TiltCard>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
