'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore, apiGet } from '@/lib/store';
import { motion, useInView } from 'framer-motion';
import {
  Target, FileText, Users, TrendingUp,
  ArrowRight, ChevronRight, Zap, Briefcase,
  Bookmark, Search
} from 'lucide-react';
import JobCard from '@/components/JobCard';
import TiltCard from '@/components/TiltCard';
import AnimatedCounter from '@/components/AnimatedCounter';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import FloatingOrbs from '@/components/FloatingOrbs';
import VerifyEmailBanner from '@/components/VerifyEmailBanner';
import CompanyLogo from '@/components/CompanyLogo';
import ApplicationFunnel, { WeeklyActivity, ResponseRateRing } from '@/components/ApplicationFunnel';
import AnimatedBeam from '@/components/AnimatedBeam';
import MagneticRipple from '@/components/MagneticRipple';
import ParallaxSection from '@/components/ParallaxSection';
import dynamic from 'next/dynamic';

const SkillNetwork = dynamic(() => import('@/components/three/SkillNetwork'), { ssr: false });

interface DashboardData {
  greeting: string;
  name: string;
  strong_matches: number;
  total_applications: number;
  interviews: number;
  saved_jobs: number;
  profile_strength: number;
  recommended_jobs: any[];
  recent_applications: any[];
  profile_tips: string[];
  unread_notifications: number;
}

interface GapEntry {
  skill: string;
  jobs_missing: number;
  critical_jobs: number;
  avg_score_gain: number;
  importance: string;
}

interface GapResponse {
  gaps: GapEntry[];
  jobs_analyzed: number;
  strong_matches: number;
}

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

function StatCard({ icon: Icon, label, value, isPercent, href }: {
  icon: any; label: string; value: number | string; isPercent?: boolean; href?: string;
}) {
  const numericValue = typeof value === 'number' ? value : parseInt(String(value).replace(/[^0-9]/g, '')) || 0;

  const content = (
    <TiltCard tiltAmount={4}>
      <div className="bg-[#050505] border border-white/[0.04] hover:border-white/[0.1] rounded-xl p-5 transition-all duration-500 relative overflow-hidden group">
        {/* Hover glow */}
        <div className="absolute -top-16 -right-16 w-32 h-32 bg-white/[0.015] rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
        <div className="relative z-10">
          <div className="flex items-center justify-between mb-4">
            <Icon size={16} className="text-white/20 group-hover:text-white/40 transition-colors duration-500" />
            <div className="w-1.5 h-1.5 rounded-full bg-white/10 group-hover:bg-white/25 transition-colors duration-500" />
          </div>
          <p className="text-3xl font-bold tracking-tight">
            <AnimatedCounter end={numericValue} suffix={isPercent ? '%' : ''} />
          </p>
          <p className="text-[11px] text-white/25 mt-1.5 uppercase tracking-wider">{label}</p>
        </div>
      </div>
    </TiltCard>
  );

  if (href) {
    return <Link href={href} className="block">{content}</Link>;
  }
  return content;
}

export default function DashboardPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [gaps, setGaps] = useState<GapEntry[]>([]);
  const [gapStats, setGapStats] = useState({ jobs_analyzed: 0, strong_matches: 0 });

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadDashboard();
  }, [user, hydrated, router]);

  const loadDashboard = async () => {
    try {
      // Skill gaps load in parallel; failure is non-fatal (card hides)
      apiGet<GapResponse>('/api/analytics/skill-gaps')
        .then((g) => {
          setGaps(g.gaps || []);
          setGapStats({ jobs_analyzed: g.jobs_analyzed || 0, strong_matches: g.strong_matches || 0 });
        })
        .catch(() => {});
      const result = await apiGet<DashboardData>('/api/dashboard');
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!hydrated || !user) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="space-y-6">
          <div className="skeleton h-10 w-80" />
          <div className="skeleton h-5 w-60" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="space-y-6">
          <div className="skeleton h-10 w-80" />
          <div className="skeleton h-5 w-60" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-28 rounded-xl" />)}
          </div>
          <div className="grid lg:grid-cols-3 gap-6 mt-8">
            <div className="lg:col-span-2 space-y-3">
              {[1, 2, 3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
            </div>
            <div className="space-y-4">
              <div className="skeleton h-40 rounded-xl" />
              <div className="skeleton h-32 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <ErrorBoundary>
    <div className="max-w-6xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-20" />
      <motion.div variants={container} initial="hidden" animate="show" className="relative z-10">
        {/* Email verification nudge (unverified accounts only) */}
        {user.email_verified === false && (
          <motion.div variants={item}>
            <VerifyEmailBanner email={user.email} />
          </motion.div>
        )}

        {/* Header with parallax depth */}
        <ParallaxSection speed={0.08} className="mb-10">
          <motion.div variants={item}>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-shimmer-slow">
              {data.greeting}, {data.name?.split(' ')[0]}
            </h1>
            <p className="text-white/30 mt-2 text-[15px]">
              {data.strong_matches > 0
                ? `You have ${data.strong_matches} strong opportunit${data.strong_matches === 1 ? 'y' : 'ies'} waiting.`
                : 'Build your profile to discover matched opportunities.'
              }
            </p>
          </motion.div>
        </ParallaxSection>

        {/* Stats */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          <StatCard icon={Target} label="Strong Matches" value={data.strong_matches} href="/jobs" />
          <StatCard icon={FileText} label="Applications" value={data.total_applications} href="/applications" />
          <StatCard icon={Users} label="Interviews" value={data.interviews} href="/applications" />
          <StatCard icon={TrendingUp} label="Profile Strength" value={Math.round(data.profile_strength)} isPercent />
        </motion.div>

        {/* Skill Network (if profile has skills) */}
        <motion.div variants={item} className="mb-8">
          <div className="bg-[#050505] border border-white/[0.04] rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-5 pt-4 pb-0">
              <h2 className="text-base font-semibold">Your skill network</h2>
              <Link href="/profile" className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors">
                Edit skills <ChevronRight size={12} />
              </Link>
            </div>
            <div className="h-[320px]">
              <SkillNetwork
                skills={(() => {
                  const allSkills: string[] = [];
                  (data.recommended_jobs || []).forEach((job: any) => {
                    try {
                      const parsed = JSON.parse(job.skills_required || '[]');
                      allSkills.push(...parsed);
                    } catch {}
                  });
                  const fallback = ['Python', 'JavaScript', 'React', 'SQL', 'Node.js', 'TypeScript', 'Git', 'FastAPI', 'Java', 'Docker'];
                  const skills = allSkills.length > 0 ? allSkills : fallback;
                  const counts: Record<string, number> = {};
                  skills.forEach((s: string) => { counts[s] = (counts[s] || 0) + 1; });
                  const sorted = Object.entries(counts)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([name, count]) => ({
                      name,
                      level: count >= 3 ? 'expert' : count >= 2 ? 'advanced' : 'intermediate',
                    }));
                  return sorted;
                })()}
                className="w-full h-full"
              />
            </div>
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recommended Jobs */}
            <motion.div variants={item}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold">Recommended for you</h2>
                <Link href="/jobs" className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors duration-200">
                  View all <ChevronRight size={12} />
                </Link>
              </div>
              {data.recommended_jobs.length > 0 ? (
                <div className="space-y-2.5">
                  {data.recommended_jobs.slice(0, 4).map((job: any, i: number) => (
                    <motion.div
                      key={job.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.08, duration: 0.5 }}
                    >
                      <JobCard key={job.id} job={job} onSaveChange={loadDashboard} />
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-12 text-center">
                  <Target size={24} className="text-white/10 mx-auto mb-3" />
                  <p className="text-white/35 text-sm">No recommendations yet</p>
                  <p className="text-white/15 text-xs mt-1.5">Complete your profile to get matched</p>
                  <Link
                    href="/onboarding"
                    className="inline-flex items-center gap-1 mt-5 text-xs text-white/40 hover:text-white/70 transition-colors"
                  >
                    Build your profile <ArrowRight size={12} />
                  </Link>
                </div>
              )}
            </motion.div>

            {/* Recent Applications */}
            {data.recent_applications.length > 0 && (
              <motion.div variants={item}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-base font-semibold">Recent applications</h2>
                  <Link href="/applications" className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors duration-200">
                    View all <ChevronRight size={12} />
                  </Link>
                </div>
                <div className="space-y-2">
                  {data.recent_applications.map((app: any) => (
                    <Link
                      key={app.id}
                      href={`/jobs/${app.job_id}`}
                      className="flex items-center gap-3 bg-[#050505] border border-white/[0.04] hover:border-white/[0.08] rounded-xl p-4 transition-all duration-300 group"
                    >
                      <CompanyLogo src={app.company_logo} name={app.company_name || ''} size="sm" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{app.job_title}</p>
                        <p className="text-xs text-white/30">{app.company_name}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className={`text-[11px] px-2.5 py-1 rounded-full capitalize ${
                          app.status === 'interview' ? 'bg-white/10 text-white' :
                          app.status === 'offer' ? 'bg-white/15 text-white' :
                          'bg-white/[0.04] text-white/40'
                        }`}>
                          {app.status}
                        </span>
                        <p className="text-[11px] text-white/15 mt-1.5">
                          {new Date(app.applied_at).toLocaleDateString()}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Analytics Section */}
            <motion.div variants={item}>
              <h2 className="text-base font-semibold mb-4">Your analytics</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                  <h4 className="text-[11px] text-white/30 uppercase tracking-wider mb-3">Application funnel</h4>
                  <ApplicationFunnel stages={[
                    { label: 'Saved', count: data.saved_jobs, color: 'bg-white/30', percentage: 100 },
                    { label: 'Applied', count: data.total_applications, color: 'bg-white/50', percentage: data.total_applications > 0 ? (data.total_applications / Math.max(data.saved_jobs, 1)) * 100 : 0 },
                    { label: 'Interviews', count: data.interviews, color: 'bg-white/70', percentage: data.interviews > 0 ? (data.interviews / Math.max(data.total_applications, 1)) * 100 : 0 },
                  ]} />
                </div>
                <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                  <h4 className="text-[11px] text-white/30 uppercase tracking-wider mb-3">Weekly activity</h4>
                  <WeeklyActivity data={[3, 5, 2, 7, 4, 1, 2]} />
                </div>
                <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5 flex flex-col items-center justify-center">
                  <h4 className="text-[11px] text-white/30 uppercase tracking-wider mb-3">Response rate</h4>
                  <ResponseRateRing rate={data.total_applications > 0 ? Math.round((data.interviews / data.total_applications) * 100) : 0} />
                </div>
              </div>
            </motion.div>
          </div>

          {/* Sidebar */}
          <motion.div variants={item} className="space-y-4">
            {/* Profile Strength */}
            <TiltCard tiltAmount={3}>
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                <h3 className="text-[13px] font-semibold mb-4">Profile Strength</h3>
                <div className="relative mb-4">
                  <div className="w-full h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${data.profile_strength}%` }}
                      transition={{ duration: 1.2, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                      className="h-full bg-white rounded-full relative"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-[shimmer_2s_infinite]" style={{ backgroundSize: '200% 100%' }} />
                    </motion.div>
                  </div>
                </div>
                <p className="text-2xl font-bold">
                  <AnimatedCounter end={Math.round(data.profile_strength)} suffix="%" />
                </p>
                <Link
                  href="/profile"
                  className="text-xs text-white/25 hover:text-white/50 mt-2 inline-flex items-center gap-1 transition-colors duration-200"
                >
                  View profile <ChevronRight size={10} />
                </Link>
              </div>
            </TiltCard>

            {/* Skill Gaps — what to improve, with honest impact estimates */}
            {gaps.length > 0 && (
              <TiltCard tiltAmount={3}>
                <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                  <h3 className="text-[13px] font-semibold mb-1 flex items-center gap-2">
                    <Target size={13} className="text-white/30" />
                    Skills to improve
                  </h3>
                  <p className="text-[10px] text-white/20 mb-4">
                    From {gapStats.strong_matches} jobs scoring 60%+
                  </p>
                  <div className="space-y-3">
                    {gaps.slice(0, 4).map((g, i) => (
                      <motion.div
                        key={g.skill}
                        initial={{ opacity: 0, x: -5 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 + i * 0.05 }}
                        className="flex items-center justify-between gap-2"
                      >
                        <div className="min-w-0">
                          <p className="text-xs text-white/60 capitalize truncate">
                            {g.importance === 'critical' ? '● ' : '○ '}{g.skill}
                          </p>
                          <p className="text-[10px] text-white/25">
                            missing from {g.jobs_missing} job{g.jobs_missing !== 1 ? 's' : ''}
                          </p>
                        </div>
                        {g.avg_score_gain > 0 && (
                          <span className="text-[10px] font-mono text-white/40 flex-shrink-0">
                            +{g.avg_score_gain.toFixed(1)}%
                          </span>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </div>
              </TiltCard>
            )}

            {/* Tips */}
            {data.profile_tips.length > 0 && (
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                <h3 className="text-[13px] font-semibold mb-4 flex items-center gap-2">
                  <Zap size={13} className="text-white/30" />
                  Improve your profile
                </h3>
                <div className="space-y-3">
                  {data.profile_tips.slice(0, 3).map((tip, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.6 + i * 0.1 }}
                      className="flex items-start gap-2.5"
                    >
                      <span className="text-white/15 text-[11px] mt-0.5 font-mono">{i + 1}.</span>
                      <p className="text-[12px] text-white/35 leading-relaxed">{tip}</p>
                    </motion.div>
                  ))}
                </div>
                <Link
                  href="/profile"
                  className="mt-4 text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors duration-200"
                >
                  Edit profile <ChevronRight size={10} />
                </Link>
              </div>
            )}

            {/* Quick Actions */}
            <MagneticRipple intensity={0.08}>
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                <h3 className="text-[13px] font-semibold mb-3">Quick actions</h3>
                <div className="space-y-1">
                  {[
                    { href: '/jobs', icon: Search, label: 'Browse jobs' },
                    { href: '/saved', icon: Bookmark, label: `Saved jobs (${data.saved_jobs})` },
                    { href: '/applications', icon: FileText, label: 'My applications' },
                  ].map((action) => (
                    <Link
                      key={action.href}
                      href={action.href}
                      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.03] transition-all duration-200 text-sm text-white/40 hover:text-white/70 group press-scale"
                    >
                      <action.icon size={14} className="group-hover:text-white/50 transition-colors" />
                      {action.label}
                    </Link>
                  ))}
                </div>
              </div>
            </MagneticRipple>
          </motion.div>
        </div>
      </motion.div>
    </div>
    </ErrorBoundary>
  );
}
