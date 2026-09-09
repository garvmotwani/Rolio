'use client';

import { Suspense } from 'react';
import JobsContent from './JobsContent';

export default function JobsPage() {
  return (
    <Suspense fallback={
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="skeleton h-10 w-48 mb-6" />
        <div className="skeleton h-12 mb-6" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-40 rounded-lg" />)}
        </div>
      </div>
    }>
      <JobsContent />
    </Suspense>
  );
}
