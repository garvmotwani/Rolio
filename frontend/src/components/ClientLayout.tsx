'use client';

import { useEffect, Suspense, lazy } from 'react';
import { useAuthStore } from '@/lib/store';
import { usePathname } from 'next/navigation';
import Navbar from './Navbar';
import Footer from './Footer';
import CustomCursor from './CustomCursor';
import PageTransition from './PageTransition';
import KeyboardShortcuts from './KeyboardShortcuts';
import ScrollToTop from './ScrollToTop';
import ScrollProgress from './ScrollProgress';
import { ToastProvider } from './Toast';

const AIChat = lazy(() => import('./AIChat'));

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const { loadFromStorage } = useAuthStore();
  const pathname = usePathname();
  const isLanding = pathname === '/';

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <ToastProvider>
      <CustomCursor />
      <div className="noise-overlay" />
      <KeyboardShortcuts />
      <ScrollProgress />
      <Navbar />
      <main id="main-content" className={`${isLanding ? '' : 'pt-14 min-h-screen'}`} role="main">
        <PageTransition>
          {children}
        </PageTransition>
        <Footer />
      </main>
      <Suspense fallback={null}>
        <AIChat />
      </Suspense>
      <ScrollToTop />
    </ToastProvider>
  );
}
