'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiGet } from '@/lib/store';
import { formatINR } from '@/lib/format';
import { motion } from 'framer-motion';
import { ArrowLeft, MapPin, Globe, Users, Briefcase, ExternalLink, ChevronRight } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import TiltCard from '@/components/TiltCard';
import CompanyLogo from '@/components/CompanyLogo';

interface CompanyData {
  id: number;
  name: string;
  logo_url: string;
  industry: string;
  location: string;
  website: string;
  description: string;
  size: string;
  founded: string;
  open_jobs_count: number;
  jobs: Array<{
    id: number;
    title: string;
    location: string;
    work_type: string;
    salary_min: number;
    salary_max: number;
    experience_level: string;
    posted_at: string;
  }>;
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export default function CompanyPage() {
  const params = useParams();
  const [company, setCompany] = useState<CompanyData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCompany();
  }, [params.id]);

  const loadCompany = async () => {
    try {
      const data = await apiGet<CompanyData>(`/api/companies/${params.id}`);
      setCompany(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10 space-y-4">
        <div className="skeleton h-10 w-48" />
        <div className="skeleton h-48 rounded-xl" />
        <div className="skeleton h-32 rounded-xl" />
      </div>
    );
  }

  if (!company) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-10" />

      <motion.div variants={container} initial="hidden" animate="show" className="relative z-10">
        {/* Back */}
        <motion.div variants={item} className="mb-6">
          <Link href="/jobs" className="inline-flex items-center gap-1.5 text-xs text-white/25 hover:text-white/50 transition-colors">
            <ArrowLeft size={14} />
            Back to jobs
          </Link>
        </motion.div>

        {/* Company Header */}
        <motion.div variants={item}>
          <div className="section-card overflow-hidden">
            <div className="p-6 md:p-8">
              <div className="flex items-start gap-5">
                <CompanyLogo src={company.logo_url} name={company.name} size="lg" />
                <div className="flex-1 min-w-0">
                  <h1 className="text-2xl md:text-3xl font-bold tracking-tight">{company.name}</h1>
                  {company.industry && (
                    <p className="text-sm text-white/35 mt-1">{company.industry}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-white/25">
                    {company.location && (
                      <span className="flex items-center gap-1"><MapPin size={12} />{company.location}</span>
                    )}
                    {company.size && (
                      <span className="flex items-center gap-1"><Users size={12} />{company.size}</span>
                    )}
                    {company.founded && (
                      <span className="flex items-center gap-1"><Briefcase size={12} />Founded {company.founded}</span>
                    )}
                    {company.website && (
                      <a
                        href={company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 hover:text-white/50 transition-colors"
                      >
                        <Globe size={12} />Website <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                </div>
              </div>

              {company.description && (
                <p className="text-sm text-white/35 leading-relaxed mt-5 pt-5 border-t border-white/[0.04]">
                  {company.description}
                </p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Open Positions */}
        <motion.div variants={item} className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold">Open Positions</h2>
            <span className="text-xs text-white/20 font-mono">{company.open_jobs_count}</span>
          </div>

          {company.jobs && company.jobs.length > 0 ? (
            <div className="space-y-2">
              {company.jobs.map((job, i) => (
                <motion.div key={job.id} variants={item}>
                  <Link href={`/jobs/${job.id}`}>
                    <TiltCard tiltAmount={1}>
                      <div className="section-card p-5 hover:border-white/[0.08] transition-all duration-300 group cursor-pointer">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-medium group-hover:text-white/90 transition-colors">
                              {job.title}
                            </h3>
                            <div className="flex items-center gap-3 mt-1.5 text-xs text-white/25">
                              <span className="flex items-center gap-1">
                                <MapPin size={11} />{job.location}
                              </span>
                              <span className="capitalize">{job.work_type}</span>
                              <span className="capitalize">{job.experience_level}</span>
                              {job.salary_min > 0 && (
                                <span>{formatINR(job.salary_min)} – {formatINR(job.salary_max)}</span>
                              )}
                            </div>
                          </div>
                          <ChevronRight size={16} className="text-white/10 group-hover:text-white/30 transition-colors flex-shrink-0" />
                        </div>
                      </div>
                    </TiltCard>
                  </Link>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="section-card p-8 text-center">
              <Briefcase size={24} className="text-white/10 mx-auto mb-3" />
              <p className="text-sm text-white/25">No open positions at this time</p>
            </div>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}
