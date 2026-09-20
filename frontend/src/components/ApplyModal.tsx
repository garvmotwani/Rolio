'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Loader2, CheckCircle, ArrowRight, FileText } from 'lucide-react';
import { useAuthStore } from '@/lib/store';
import { apiPost, apiGet } from '@/lib/api';
import { useToast } from './Toast';

interface ApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: number | string;
  jobTitle: string;
  companyName: string;
  applicationUrl?: string;
  onApplied?: () => void;
}


interface ResumeOption { id: number; filename: string; uploaded_at: string; }

export default function ApplyModal({ isOpen, onClose, jobId, jobTitle, companyName, applicationUrl, onApplied }: ApplyModalProps) {
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isApplied, setIsApplied] = useState(false);
  const [resumes, setResumes] = useState<ResumeOption[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const user = useAuthStore(s => s.user);
  const { addToast } = useToast();

  // Load the current resume when the modal opens — attributing applications
  // to a resume version enables per-version response-rate analytics.
  // Failure is silent — resume attribution is optional.
  useEffect(() => {
    if (!isOpen) return;
    apiGet<{ resume: (ResumeOption & Record<string, unknown>) | null }>('/api/resume')
      .then((r) => {
        if (r.resume) {
          setResumes([r.resume]);
          setResumeId(r.resume.id);
        }
      })
      .catch(() => {});
  }, [isOpen]);

  const handleApply = async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      await apiPost('/api/applications', {
        // Local jobs pass numeric ids; external jobs pass prefixed string ids
        // (jsearch_/remotive_/jobicy_) — the backend imports them to the DB.
        job_id: jobId,
        notes: notes || undefined,
        external_url: applicationUrl || undefined,
        resume_id: resumeId || undefined,
      });
      setIsApplied(true);
      addToast(`Applied to ${jobTitle} at ${companyName}`, 'success');
      setTimeout(() => { onApplied?.(); onClose(); setIsApplied(false); }, 1500);
    } catch (err) {
      addToast(err instanceof Error ? err.message : 'Failed to apply', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[9990]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-[9999]"
            role="dialog"
            aria-label={`Apply to ${jobTitle}`}
          >
            <div className="bg-[#0a0a0a] border border-white/10 rounded-2xl shadow-2xl p-6">
              {isApplied ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center py-8"
                >
                  <CheckCircle size={48} className="text-white mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Application submitted!</h3>
                  <p className="text-sm text-white/50">
                    Applied to <strong className="text-white/80">{jobTitle}</strong> at <strong className="text-white/80">{companyName}</strong>
                  </p>
                </motion.div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-base font-semibold">Apply to job</h3>
                      <p className="text-xs text-white/40 mt-0.5">{jobTitle} at {companyName}</p>
                    </div>
                    <button
                      onClick={onClose}
                      className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/40 hover:text-white/80 transition-colors"
                      aria-label="Close"
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="text-[11px] text-white/40 uppercase tracking-wider block mb-1.5">
                        Notes (optional)
                      </label>
                      <textarea
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        placeholder="Add notes about this application..."
                        rows={3}
                        className="w-full bg-white/[0.03] border border-white/5 rounded-xl px-3.5 py-2.5 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-white/15 transition-colors resize-none"
                      />
                    </div>

                    {resumes.length > 0 && (
                      <div>
                        <label className="text-[11px] text-white/40 uppercase tracking-wider block mb-1.5">
                          Resume used
                        </label>
                        <div className="space-y-1.5">
                          {resumes.map((r) => (
                            <button
                              key={r.id}
                              type="button"
                              onClick={() => setResumeId(r.id)}
                              className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border text-left transition-all ${
                                resumeId === r.id
                                  ? 'border-white/25 bg-white/[0.06]'
                                  : 'border-white/5 bg-white/[0.02] hover:bg-white/[0.04]'
                              }`}
                            >
                              <FileText size={14} className={resumeId === r.id ? 'text-white/80' : 'text-white/30'} />
                              <span className="text-sm text-white/70 truncate flex-1">{r.filename}</span>
                              {resumeId === r.id && <CheckCircle size={14} className="text-white/60 flex-shrink-0" />}
                            </button>
                          ))}
                        </div>
                        <p className="text-[10px] text-white/20 mt-1.5">
                          Tracks which version performs best across your applications
                        </p>
                      </div>
                    )}

                    <div className="flex gap-3">
                      {applicationUrl && (
                        <a
                          href={applicationUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.05] border border-white/5 text-sm text-white/60 hover:text-white/80 hover:bg-white/[0.08] transition-all"
                        >
                          <ExternalLink size={14} />
                          Open job page
                        </a>
                      )}
                      <button
                        onClick={handleApply}
                        disabled={isLoading}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white text-black text-sm font-medium hover:bg-white/90 disabled:opacity-50 transition-all"
                      >
                        {isLoading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                        {isLoading ? 'Applying...' : 'Mark as applied'}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
