'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';

const footerLinks = {
  Product: [
    { label: 'Job Search', href: '/jobs' },
    { label: 'Applications', href: '/applications' },
    { label: 'Saved Jobs', href: '/saved' },
    { label: 'Settings', href: '/settings' },
  ],
  Account: [
    { label: 'Profile', href: '/profile' },
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Onboarding', href: '/onboarding' },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '#' },
    { label: 'Terms of Service', href: '#' },
  ],
};

export default function Footer() {
  const pathname = usePathname();
  const isLanding = pathname === '/';

  // Don't show footer on landing page (it has its own footer)
  if (isLanding) return null;

  return (
    <footer className="border-t border-white/[0.04] mt-20">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="text-lg font-bold tracking-tight inline-block mb-3">
              RO<span className="text-white/30">LIO</span>
            </Link>
            <p className="text-xs text-white/20 leading-relaxed max-w-[200px]">
              AI-powered career platform that matches you with your perfect role.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h3 className="text-[10px] uppercase tracking-[0.15em] text-white/20 font-medium mb-3">
                {category}
              </h3>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-xs text-white/30 hover:text-white/60 transition-colors duration-200"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="mt-10 pt-6 border-t border-white/[0.03] flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-[11px] text-white/15">
            &copy; {new Date().getFullYear()} Rolio. All rights reserved.
          </p>
          <p className="text-[10px] text-white/10">
            Built with precision. Powered by AI.
          </p>
        </div>
      </div>
    </footer>
  );
}
