'use client';

import { motion } from 'framer-motion';

export function SkeletonPulse({ className = '' }: { className?: string }) {
  return (
    <div className={`relative overflow-hidden bg-white/[0.04] rounded-xl ${className}`}>
      <motion.div
        className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/[0.06] to-transparent"
        animate={{ translateX: ['100%', '-100%'] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
}

export function JobCardSkeleton() {
  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 space-y-4">
      <div className="flex items-start gap-3">
        <SkeletonPulse className="w-10 h-10 rounded-xl shrink-0" />
        <div className="flex-1 space-y-2">
          <SkeletonPulse className="h-4 w-3/4" />
          <SkeletonPulse className="h-3 w-1/2" />
        </div>
        <SkeletonPulse className="h-6 w-12 rounded-full" />
      </div>
      <div className="space-y-2">
        <SkeletonPulse className="h-3 w-full" />
        <SkeletonPulse className="h-3 w-5/6" />
      </div>
      <div className="flex gap-2">
        <SkeletonPulse className="h-6 w-16 rounded-full" />
        <SkeletonPulse className="h-6 w-20 rounded-full" />
        <SkeletonPulse className="h-6 w-14 rounded-full" />
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <SkeletonPulse className="h-8 w-64" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-white/[0.03] border border-white/5 rounded-2xl p-5 space-y-3">
            <SkeletonPulse className="h-4 w-20" />
            <SkeletonPulse className="h-8 w-16" />
            <SkeletonPulse className="h-3 w-24" />
          </div>
        ))}
      </div>
      <div className="space-y-4">
        <SkeletonPulse className="h-5 w-40" />
        {[1, 2, 3].map(i => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonPulse className="h-8 w-48" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white/[0.03] border border-white/5 rounded-2xl p-6 space-y-4">
          <SkeletonPulse className="h-20 w-20 rounded-full mx-auto" />
          <SkeletonPulse className="h-5 w-32 mx-auto" />
          <SkeletonPulse className="h-3 w-48 mx-auto" />
        </div>
        <div className="lg:col-span-2 space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 space-y-3">
              <SkeletonPulse className="h-5 w-32" />
              <SkeletonPulse className="h-3 w-full" />
              <SkeletonPulse className="h-3 w-3/4" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PageHeaderSkeleton() {
  return (
    <div className="space-y-3 mb-8">
      <SkeletonPulse className="h-8 w-48" />
      <SkeletonPulse className="h-4 w-80" />
    </div>
  );
}
