'use client';

import React from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="min-h-[40vh] flex items-center justify-center px-6">
          <div className="text-center max-w-sm">
            <div className="w-14 h-14 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mx-auto mb-4">
              <AlertTriangle size={24} className="text-amber-400/60" />
            </div>
            <h3 className="text-sm font-semibold mb-2">Something went wrong</h3>
            <p className="text-xs text-white/25 mb-5 leading-relaxed">
              This section hit an unexpected error. You can try reloading it.
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="inline-flex items-center gap-2 bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.06] rounded-lg px-4 py-2 text-xs font-medium text-white/60 hover:text-white/80 transition-all"
            >
              <RefreshCcw size={12} /> Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
