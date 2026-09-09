'use client';

import Link from 'next/link';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Clock, Bookmark, BookmarkCheck, Briefcase } from 'lucide-react';
import { apiPost, apiDelete } from '@/lib/store';
import { formatINR } from '@/lib/format';
import { useToast } from '@/components/Toast';
import TiltCard from '@/components/TiltCard';
import CompanyLogo from '@/components/CompanyLogo';
import AnimatedScoreRing from '@/components/AnimatedScoreRing';

interface Job {
  id: number | string;
  title: string;
  company_name: string;
  company_logo?: string;
  location: string;
  work_type: string;
  salary_min?: number;
  salary_max?: number;
  experience_level?: string;
  skills_required?: string;
  match_score?: number;
  posted_at: string;
  is_saved?: boolean;
  is_applied?: boolean;
}

function parseSkills(s?: string | string[]): string[] {
  if (!s) return [];
  if (Array.isArray(s)) return s.filter(Boolean);
  try { return JSON.parse(s); } catch { return s.split(',').map(x => x.trim()).filter(Boolean); }
}

function formatSalary(min?: number, max?: number): string {
  if (!min && !max) return '';
  const fmt = (n: number) => formatINR(n);
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  if (min) return `From ${fmt(min)}`;
  return `Up to ${fmt(max!)}`;
}

function timeAgo(date: string): string {
  const diff = Date.now() - new Date(date).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'Today';
  if (days === 1) return '1 day ago';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

export default function JobCard({ job, onSaveChange }: { job: Job; onSaveChange?: () => void }) {
  const [saved, setSaved] = useState(job.is_saved || false);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const handleSave = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (saving) return;
    setSaving(true);
    try {
      if (saved) {
        await apiDelete(`/api/jobs/${job.id}/save`);
        setSaved(false);
        addToast(`Unsaved "${job.title}"`, 'info');
      } else {
        await apiPost(`/api/jobs/${job.id}/save`);
        setSaved(true);
        addToast(`Saved "${job.title}"`, 'success');
      }
      onSaveChange?.();
    } catch (err) {
      addToast('Failed to save job', 'error');
    } finally {
      setSaving(false);
    }
  };

  const skills = parseSkills((job as any).skills_required || (job as any).skills);
  const score = job.match_score ? Math.round(job.match_score) : null;
  const isStrong = score !== null && score >= 80;

  return (
    <Link href={`/jobs/${job.id}`} className="block group">
      <TiltCard tiltAmount={3}>
        <motion.div
          className="bg-[#050505] border border-white/[0.04] hover:border-white/[0.12] rounded-xl p-5 transition-all duration-500 relative overflow-hidden"
          whileHover={{ y: -2 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          {/* Hover gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/[0.015] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

          {/* Strong match glow */}
          {isStrong && (
            <motion.div
              className="absolute -top-8 -right-8 w-32 h-32 bg-white/[0.03] rounded-full blur-2xl pointer-events-none"
              animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            />
          )}

          {/* Cursor spotlight */}
          <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            style={{ background: 'radial-gradient(circle 200px at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255,255,255,0.02), transparent)' }}
          />

          <div className="relative z-10">
            {/* Header row */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <CompanyLogo
                  src={job.company_logo}
                  name={job.company_name || ''}
                  size="md"
                  className="flex-shrink-0 group-hover:border-white/[0.12] transition-colors duration-500 group-hover:shadow-[0_0_12px_rgba(255,255,255,0.03)]"
                />
                <div className="min-w-0">
                  <h3 className="text-[15px] font-semibold truncate group-hover:text-white transition-colors duration-300">
                    {job.title}
                  </h3>
                  <p className="text-xs text-white/30 mt-0.5 group-hover:text-white/40 transition-colors duration-300">
                    {job.company_name}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 flex-shrink-0">
                {score !== null && (
                  <AnimatedScoreRing score={score} size={44} strokeWidth={3} />
                )}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="p-1.5 rounded-lg hover:bg-white/5 transition-all duration-300 active:scale-90"
                  aria-label={saved ? 'Unsave job' : 'Save job'}
                >
                  {saved ? (
                    <BookmarkCheck size={16} className="text-white/60" />
                  ) : (
                    <Bookmark size={16} className="text-white/20 group-hover:text-white/40 transition-colors duration-300" />
                  )}
                </button>
              </div>
            </div>

            {/* Meta row */}
            <div className="flex items-center gap-3 mt-3.5 flex-wrap">
              <span className="flex items-center gap-1 text-xs text-white/25 group-hover:text-white/35 transition-colors duration-300">
                <MapPin size={12} /> {job.location}
              </span>
              {job.work_type && (
                <span className="flex items-center gap-1 text-xs text-white/20 capitalize group-hover:text-white/30 transition-colors duration-300">
                  <Briefcase size={11} /> {job.work_type}
                </span>
              )}
              {job.salary_min && job.salary_min > 0 ? (
                <span className="text-xs text-white/20 group-hover:text-white/30 transition-colors duration-300">
                  {formatSalary(job.salary_min, job.salary_max)}
                </span>
              ) : null}
              {(job as any).source === 'jsearch' && (
                <span className="text-[10px] px-1.5 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded text-white/30 ml-auto">
                  Live
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-white/15 ml-auto group-hover:text-white/25 transition-colors duration-300">
                <Clock size={11} /> {timeAgo(job.posted_at)}
              </span>
            </div>

            {/* Skills row */}
            {skills.length > 0 && (
              <div className="flex items-center gap-1.5 mt-3.5 flex-wrap">
                {skills.slice(0, 5).map((skill, i) => (
                  <motion.span
                    key={skill}
                    className="text-[11px] px-2 py-0.5 bg-white/[0.03] border border-white/[0.03] rounded text-white/35 group-hover:border-white/[0.07] group-hover:text-white/50 transition-all duration-500"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    {skill}
                  </motion.span>
                ))}
                {job.experience_level && (
                  <span className="text-[11px] px-2 py-0.5 bg-white/[0.05] border border-white/[0.05] rounded text-white/45 capitalize ml-1">
                    {job.experience_level}
                  </span>
                )}
                {isStrong && (
                  <span className="text-[11px] px-2 py-0.5 bg-white/[0.08] border border-white/[0.08] rounded text-white/60 ml-auto font-medium">
                    Strong
                  </span>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </TiltCard>
    </Link>
  );
}
