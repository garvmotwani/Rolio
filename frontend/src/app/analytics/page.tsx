'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet } from '@/lib/store';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Briefcase, CheckCircle2, XCircle, Bookmark, Activity, Sparkles } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';

interface AnalyticsData {
  summary: {
    total_applications: number;
    active_applications: number;
    offers: number;
    rejected: number;
    saved_jobs: number;
    response_rate: number;
    interview_rate: number;
    offer_rate: number;
  };
  status_distribution: Record<string, number>;
  match_scores: {
    average: number;
    min: number;
    max: number;
    buckets: Record<string, number>;
  };
  applications_over_time: { week: string; count: number }[];
  profile_skills: { name: string; level: string }[];
  company_distribution: { company: string; count: number }[];
  recent_activity: {
    id: number;
    status: string;
    applied_at: string | null;
    updated_at: string | null;
    job_title: string;
    company_name: string;
  }[];
}

interface RoadmapData {
  target_role: string;
  has_profile: boolean;
  message?: string;
  readiness?: number;
  matching_jobs?: number;
  steps: { skill: string; jobs_missing: number; avg_readiness_gain: number; priority: number }[];
}

export default function AnalyticsPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(90);
  const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadAnalytics();
  }, [user, hydrated, router, days]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const d = await apiGet<AnalyticsData>(`/api/analytics/dashboard?days=${days}`);
      setData(d);
      // Non-fatal: roadmap section hides if unavailable
      apiGet<RoadmapData>('/api/analytics/career-roadmap').then(setRoadmap).catch(() => setRoadmap(null));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-64 rounded-xl" />)}
        </div>
      </div>
    );
  }

  const { summary, status_distribution, match_scores, applications_over_time, company_distribution, recent_activity } = data;

  const statCards = [
    { label: 'Total Applications', value: summary.total_applications, icon: Briefcase, sub: 'all time' },
    { label: 'Active', value: summary.active_applications, icon: Activity, sub: 'in progress' },
    { label: 'Offers', value: summary.offers, icon: CheckCircle2, sub: `${summary.offer_rate}% offer rate` },
    { label: 'Rejected', value: summary.rejected, icon: XCircle, sub: 'so far' },
    { label: 'Saved Jobs', value: summary.saved_jobs, icon: Bookmark, sub: 'bookmarked' },
    { label: 'Response Rate', value: `${summary.response_rate}%`, icon: TrendingUp, sub: 'engagements / viewed' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-10" />

      <div className="relative z-10">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight flex items-center gap-3">
                Analytics
                <span className="inline-flex items-center gap-1.5 text-[10px] font-medium text-white/30 bg-white/[0.04] border border-white/[0.06] rounded-full px-2.5 py-1">
                  <Sparkles size={10} /> Insights
                </span>
              </h1>
              <p className="text-white/30 text-sm mt-1">Your application funnel, at a glance</p>
            </div>
            <div className="flex items-center gap-1 bg-white/[0.03] border border-white/[0.06] rounded-full p-1">
              {[30, 90, 180].map(d => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${
                    days === d ? 'bg-white text-black font-medium' : 'text-white/35 hover:text-white/60'
                  }`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* ─── Stat Cards ─── */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
          {statCards.map((card, i) => {
            const Icon = card.icon;
            return (
              <motion.div
                key={card.label}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="bg-[#050505] border border-white/[0.05] hover:border-white/[0.1] rounded-xl p-4 transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] uppercase tracking-wider text-white/25">{card.label}</span>
                  <Icon size={13} className="text-white/20" />
                </div>
                <p className="text-2xl font-bold tracking-tight">{card.value}</p>
                <p className="text-[10px] text-white/20 mt-1">{card.sub}</p>
              </motion.div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* ─── Status Distribution ─── */}
          <ChartCard title="Status Distribution" subtitle="Where your applications stand">
            <StatusBars dist={status_distribution} total={summary.total_applications} />
          </ChartCard>

          {/* ─── Applications Over Time ─── */}
          <ChartCard title="Applications Over Time" subtitle={`Weekly volume · last ${days} days`}>
            <LineChart data={applications_over_time} />
          </ChartCard>

          {/* ─── Match Score Distribution ─── */}
          <ChartCard
            title="Match Score Distribution"
            subtitle={`Avg ${match_scores.average}% · range ${match_scores.min}–${match_scores.max}%`}
          >
            <ScoreBars buckets={match_scores.buckets} />
          </ChartCard>

          {/* ─── Top Companies ─── */}
          <ChartCard title="Top Companies" subtitle="Where you apply most">
            <CompanyBars companies={company_distribution} />
          </ChartCard>
        </div>

        {/* ─── Career Roadmap (data-driven, from real listings) ─── */}
        {roadmap && roadmap.target_role && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-[#050505] border border-white/[0.05] rounded-xl p-6 mb-6"
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 className="text-sm font-semibold">Roadmap to {roadmap.target_role}</h3>
                {roadmap.readiness != null ? (
                  <p className="text-xs text-white/25 mt-1">
                    Current readiness {roadmap.readiness}% across {roadmap.matching_jobs} matching jobs
                  </p>
                ) : (
                  <p className="text-xs text-white/25 mt-1">{roadmap.message}</p>
                )}
              </div>
              {roadmap.readiness != null && (
                <div className="text-right flex-shrink-0">
                  <p className="text-2xl font-bold">{roadmap.readiness}%</p>
                  <p className="text-[10px] text-white/25 uppercase tracking-wider">ready</p>
                </div>
              )}
            </div>
            {roadmap.steps.length > 0 && (
              <div className="space-y-2">
                {roadmap.steps.map((s, i) => (
                  <motion.div
                    key={s.skill}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.04 }}
                    className="flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-white/[0.02] transition-colors"
                  >
                    <span className="text-[10px] font-mono text-white/20 w-5">{i + 1}.</span>
                    <span className="text-[13px] text-white/60 capitalize flex-1">{s.skill}</span>
                    <span className="text-[11px] text-white/25">
                      {s.jobs_missing}/{roadmap.matching_jobs} target jobs
                    </span>
                    {s.avg_readiness_gain > 0 && (
                      <span className="text-[11px] font-mono text-white/45 w-14 text-right">+{s.avg_readiness_gain}%</span>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* ─── Recent Activity ─── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-[#050505] border border-white/[0.05] rounded-xl p-6"
        >
          <h3 className="text-sm font-semibold mb-1">Recent Activity</h3>
          <p className="text-xs text-white/25 mb-4">Latest application updates</p>

          {recent_activity.length === 0 ? (
            <p className="text-sm text-white/20 py-8 text-center">No activity yet — apply to jobs to see your history here.</p>
          ) : (
            <div className="space-y-1">
              {recent_activity.map((item, i) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-3 py-2.5 px-2 rounded-lg hover:bg-white/[0.02] transition-colors"
                >
                  <div className="w-2 h-2 rounded-full bg-white/30 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] text-white/60 truncate">{item.job_title}</p>
                    <p className="text-[11px] text-white/20 truncate">{item.company_name}</p>
                  </div>
                  <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded-full bg-white/[0.05] border border-white/[0.06] text-white/35">
                    {item.status}
                  </span>
                  <span className="text-[10px] text-white/20 w-16 text-right flex-shrink-0">
                    {item.updated_at ? formatShortDate(item.updated_at) : '—'}
                  </span>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {summary.total_applications === 0 && (
          <div className="mt-8 text-center">
            <Link href="/jobs" className="btn-premium inline-flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-full text-sm font-medium">
              Start applying <TrendingUp size={14} />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Card wrapper ─── */
function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#050505] border border-white/[0.05] hover:border-white/[0.08] rounded-xl p-6 transition-all duration-300"
    >
      <h3 className="text-sm font-semibold mb-0.5">{title}</h3>
      <p className="text-xs text-white/25 mb-5">{subtitle}</p>
      {children}
    </motion.div>
  );
}

/* ─── Status bar chart ─── */
function StatusBars({ dist, total }: { dist: Record<string, number>; total: number }) {
  const statuses = ['applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn'];
  const labels: Record<string, string> = {
    applied: 'Applied', screening: 'Screening', interview: 'Interview',
    offer: 'Offer', rejected: 'Rejected', withdrawn: 'Withdrawn',
  };

  const max = Math.max(...statuses.map(s => dist[s] || 0), 1);

  return (
    <div className="space-y-3">
      {statuses.map((status) => {
        const count = dist[status] || 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        const height = Math.max((count / max) * 120, count > 0 ? 6 : 2);
        return (
          <div key={status} className="flex items-center gap-3">
            <span className="w-20 text-[11px] text-white/35 capitalize flex-shrink-0">{labels[status]}</span>
            <div className="flex-1 h-[10px] bg-white/[0.03] rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.max(pct, count > 0 ? 4 : 0)}%` }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className={`h-full rounded-full ${count > 0 ? 'bg-white/40' : 'bg-white/[0.02]'}`}
              />
            </div>
            <span className="w-8 text-right text-[11px] font-mono text-white/50 flex-shrink-0">{count}</span>
          </div>
        );
      })}
      {total === 0 && <p className="text-xs text-white/20 text-center py-4">No applications tracked yet</p>}
    </div>
  );
}

/* ─── Line / area chart (SVG) ─── */
function LineChart({ data }: { data: { week: string; count: number }[] }) {
  const W = 520;
  const H = 140;
  const PAD = 8;

  if (data.length === 0 || data.every(d => d.count === 0)) {
    return <div className="h-[140px] flex items-center justify-center text-xs text-white/20">No data in this period</div>;
  }

  const max = Math.max(...data.map(d => d.count), 1);
  const stepX = (W - PAD * 2) / Math.max(data.length - 1, 1);
  const points = data.map((d, i) => ({
    x: PAD + i * stepX,
    y: H - PAD - (d.count / max) * (H - PAD * 2),
  }));

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${H - PAD} L ${points[0].x.toFixed(1)} ${H - PAD} Z`;
  const last = points[points.length - 1];
  const lastCount = data[data.length - 1].count;

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Applications over time line chart">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.18)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        {/* grid lines */}
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f} x1={PAD} x2={W - PAD} y1={H * f} y2={H * f} stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
        ))}
        <path d={areaPath} fill="url(#areaGrad)" />
        <path d={linePath} fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={last.x} cy={last.y} r="3.5" fill="white" />
      </svg>
      <div className="absolute right-1 top-1 text-[10px] font-mono text-white/40 bg-white/[0.04] px-1.5 py-0.5 rounded">
        {lastCount} this week
      </div>
      <div className="flex justify-between mt-2">
        <span className="text-[10px] text-white/20">{data[0].week}</span>
        <span className="text-[10px] text-white/20">{data[data.length - 1].week}</span>
      </div>
    </div>
  );
}

/* ─── Score bucket bars ─── */
function ScoreBars({ buckets }: { buckets: Record<string, number> }) {
  const entries = Object.entries(buckets);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div className="flex items-end gap-2 h-[140px]">
      {entries.map(([label, count]) => {
        const h = Math.max((count / max) * 120, count > 0 ? 8 : 2);
        return (
          <div key={label} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
            <span className="text-[10px] font-mono text-white/40">{count || ''}</span>
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: `${h}px` }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className={`w-full max-w-[48px] rounded-t-md ${count > 0 ? 'bg-white/35' : 'bg-white/[0.03]'}`}
            />
            <span className="text-[9px] text-white/25">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Company horizontal bars ─── */
function CompanyBars({ companies }: { companies: { company: string; count: number }[] }) {
  if (companies.length === 0) {
    return <div className="h-[140px] flex items-center justify-center text-xs text-white/20">No company data yet</div>;
  }
  const max = Math.max(...companies.map(c => c.count), 1);
  return (
    <div className="space-y-2.5">
      {companies.map((c, i) => (
        <div key={c.company} className="flex items-center gap-3">
          <span className="w-28 text-[11px] text-white/40 truncate flex-shrink-0">{c.company}</span>
          <div className="flex-1 h-[8px] bg-white/[0.03] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(c.count / max) * 100}%` }}
              transition={{ duration: 0.7, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full bg-white/35"
            />
          </div>
          <span className="w-6 text-right text-[11px] font-mono text-white/50 flex-shrink-0">{c.count}</span>
        </div>
      ))}
    </div>
  );
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}