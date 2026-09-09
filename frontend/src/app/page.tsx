'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { motion, useInView, useScroll, useTransform, useSpring } from 'framer-motion';
import { ArrowRight, Zap, Target, BarChart3, FileCheck, Search, Users, Briefcase, ChevronRight, Sparkles, Brain, LineChart, Rocket } from 'lucide-react';
import dynamic from 'next/dynamic';
import TiltCard from '@/components/TiltCard';
import MagneticButton from '@/components/MagneticButton';
import TextScramble from '@/components/TextScramble';
import GradientBorder from '@/components/GradientBorder';
import AnimatedBorder from '@/components/AnimatedBorder';
import ParticleField from '@/components/ParticleField';
import ParallaxSection from '@/components/ParallaxSection';

// Lazy-load heavy visual components to reduce initial bundle
const ParticleHero = dynamic(() => import('@/components/three/ParticleHero'), { ssr: false, loading: () => <div className="absolute inset-0 bg-black" /> });
const FloatingOrbs = dynamic(() => import('@/components/FloatingOrbs'), { ssr: false });
const GradientMesh = dynamic(() => import('@/components/GradientMesh'), { ssr: false });

/* ─── Scroll-triggered Section ─── */
function FadeInSection({ children, className = '', delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ─── Animated Counter ─── */
function AnimatedStat({ value, label, delay = 0 }: { value: string; label: string; delay?: number }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className="text-center"
    >
      <p className="text-3xl md:text-4xl font-bold tracking-tight">{value}</p>
      <p className="text-xs text-white/25 mt-2 tracking-wider uppercase">{label}</p>
    </motion.div>
  );
}

/* ─── Data ─── */
const steps = [
  { num: '01', title: 'Build your profile', desc: 'Import your resume or enter your skills, experience, education, and career preferences.', icon: Users },
  { num: '02', title: 'Rolio understands you', desc: 'Our engine analyzes your skills, experience level, and preferences to build your career profile.', icon: Brain },
  { num: '03', title: 'Discover matched opportunities', desc: 'Get ranked job recommendations with explainable match scores showing exactly why each job fits.', icon: Target },
  { num: '04', title: 'Apply and track', desc: 'Save jobs, apply directly, and manage your entire application pipeline from one dashboard.', icon: FileCheck },
];

const features = [
  { icon: BarChart3, title: 'Explainable Match Scores', desc: "Every recommendation shows exactly which skills, experience, and preferences match — and which don't.", gradient: 'from-white/5 to-transparent' },
  { icon: Search, title: 'Intelligent Search', desc: 'Search by title, skill, company, or location. Filter by work type, experience level, and salary.', gradient: 'from-white/5 to-transparent' },
  { icon: Briefcase, title: 'Application Tracker', desc: 'Track every application from saved to applied to interview to offer. Never lose track again.', gradient: 'from-white/5 to-transparent' },
  { icon: Zap, title: 'AI Career Assistant', desc: 'Ask about resume improvements, skill gaps, interview prep, and career strategy.', gradient: 'from-white/5 to-transparent' },
  { icon: Brain, title: 'Resume Intelligence', desc: 'Upload your resume and Rolio extracts skills, experience, and education to power your matches.', gradient: 'from-white/5 to-transparent' },
  { icon: Rocket, title: 'Career Roadmap', desc: 'Get personalized career advice and skill gap analysis to level up your profile.', gradient: 'from-white/5 to-transparent' },
];

/* ─── Bento Feature Card ─── */
function BentoCard({ feature, index }: { feature: typeof features[0]; index: number }) {
  const Icon = feature.icon;
  return (
    <TiltCard className="rounded-2xl" tiltAmount={4}>
      <div className="p-6 md:p-8 bg-[#030303] border border-white/[0.04] hover:border-white/[0.12] rounded-2xl transition-all duration-500 group relative overflow-hidden h-full hover-lift">
        {/* Glow effect on hover */}
        <div className="absolute -top-20 -right-20 w-40 h-40 bg-white/[0.025] rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/[0.015] rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
        <div className="relative z-10">
          <div className="w-11 h-11 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-5 group-hover:bg-white/[0.1] group-hover:border-white/[0.12] transition-all duration-500 group-hover:shadow-[0_0_16px_rgba(255,255,255,0.04)]">
            <Icon size={18} className="text-white/30 group-hover:text-white/70 transition-colors duration-500" />
          </div>
          <h3 className="text-base font-semibold mb-2.5 group-hover:text-white transition-colors">{feature.title}</h3>
          <p className="text-sm text-white/30 leading-relaxed">{feature.desc}</p>
        </div>
      </div>
    </TiltCard>
  );
}

/* ─── Landing Page ─── */
export default function LandingPage() {
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.15], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.15], [1, 0.97]);
  const heroY = useTransform(scrollYProgress, [0, 0.15], [0, 60]);
  const smoothProgress = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  return (
    <div className="bg-black text-white overflow-hidden">
      {/* ─── Hero ─── */}
      <motion.section
        style={{ opacity: heroOpacity, scale: heroScale }}
        className="relative min-h-screen flex items-center justify-center overflow-hidden"
      >
        {/* 3D Particle Background */}
        <ParticleHero />

        {/* Animated gradient mesh */}
        <GradientMesh intensity={0.8} />

        {/* Particle field with mouse parallax */}
        <ParticleField count={80} mouseInfluence={0.015} />

        {/* Floating orbs for depth */}
        <FloatingOrbs count={4} />

        {/* Animated color gradient overlay */}
        <div className="absolute inset-0 pointer-events-none z-0 animate-gradient-shift" style={{
          background: 'linear-gradient(135deg, rgba(88,28,135,0.08) 0%, rgba(30,58,138,0.06) 25%, rgba(15,23,42,0) 50%, rgba(88,28,135,0.05) 75%, rgba(30,58,138,0.08) 100%)',
          backgroundSize: '400% 400%',
        }} />

        {/* Vignette overlay */}
        <div className="absolute inset-0 pointer-events-none z-[1]" style={{
          background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.7) 100%)',
        }} />

        <motion.div style={{ y: heroY }} className="relative z-10 text-center px-6 max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full mb-8 pulse-ring"
            >
              <Sparkles size={12} className="text-white/40" />
              <span className="text-[11px] text-white/40 tracking-wider uppercase">AI-Powered Career Platform</span>
            </motion.div>

            <h1 className="text-5xl md:text-7xl lg:text-[5.5rem] font-bold leading-[0.9] tracking-tight mb-8">
              <motion.span
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="block"
              >
                <TextScramble text="Stop searching." delay={400} />
              </motion.span>
              <motion.span
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="block text-white/25"
              >
                <TextScramble text="Start matching." delay={800} />
              </motion.span>
            </h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="text-lg md:text-xl text-white/35 max-w-2xl mx-auto mb-12 leading-relaxed"
            >
              Rolio uses your skills, experience, and career goals to find opportunities that actually fit you
              — then explains exactly why.
            </motion.p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.9 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-5"
          >
            <MagneticButton href="/signup" className="btn-premium group bg-white text-black px-8 py-4 rounded-full font-semibold text-sm flex items-center gap-2.5 shadow-[0_0_40px_rgba(255,255,255,0.06)]">
              Find Your Next Job
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform duration-300" />
            </MagneticButton>
            <a
              href="#how-it-works"
              className="text-sm text-white/25 hover:text-white/50 transition-colors duration-300 flex items-center gap-1"
            >
              See How It Works
              <ChevronRight size={14} />
            </a>
          </motion.div>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 2, duration: 0.5 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10"
        >
          <div className="w-5 h-8 border border-white/15 rounded-full flex justify-center pt-2">
            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
              className="w-[3px] h-[3px] bg-white/30 rounded-full"
            />
          </div>
        </motion.div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-black to-transparent pointer-events-none z-10" />
      </motion.section>

      {/* ─── Stats bar ─── */}
      <ParallaxSection speed={0.1} className="py-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.015] to-transparent pointer-events-none" />
        <div className="absolute inset-0 border-y border-white/[0.04] pointer-events-none" />
        <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 relative z-10">
          <AnimatedStat value="20+" label="Job Listings" delay={0} />
          <AnimatedStat value="12+" label="Companies" delay={0.1} />
          <AnimatedStat value="15+" label="Skill Categories" delay={0.2} />
          <AnimatedStat value="<1s" label="Match Speed" delay={0.3} />
        </div>
      </ParallaxSection>

      {/* ─── How It Works ─── */}
      <section id="how-it-works" className="py-28 md:py-36 relative">
        <FloatingOrbs count={2} className="opacity-30" />
        <div className="max-w-6xl mx-auto px-6 relative z-10">
          <FadeInSection>
            <p className="text-xs tracking-[0.3em] text-white/20 mb-4 uppercase">Process</p>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-20">
              How Rolio works
            </h2>
          </FadeInSection>

          <div className="grid md:grid-cols-2 gap-4">
            {steps.map((step, i) => (
              <FadeInSection key={step.num} delay={i * 0.1}>
                <div className="p-8 md:p-10 bg-[#030303] border border-white/[0.04] hover:border-white/[0.1] rounded-2xl transition-all duration-700 group relative overflow-hidden hover-lift">
                  {/* Subtle corner glow */}
                  <div className="absolute top-0 right-0 w-40 h-40 bg-white/[0.015] rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                  <div className="flex items-start gap-6">
                    <div className="relative">
                      <span className="text-[11px] text-white/15 font-mono tracking-wider block mb-2">{step.num}</span>
                      <div className="w-12 h-12 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center group-hover:bg-white/[0.08] group-hover:border-white/[0.12] transition-all duration-500 group-hover:shadow-[0_0_20px_rgba(255,255,255,0.03)]">
                        <step.icon size={20} className="text-white/25 group-hover:text-white/60 transition-colors duration-500" />
                      </div>
                    </div>
                    <div className="relative z-10">
                      <h3 className="text-lg font-semibold mb-3 group-hover:text-white transition-colors">{step.title}</h3>
                      <p className="text-sm text-white/30 leading-relaxed">{step.desc}</p>
                    </div>
                  </div>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <ParallaxSection speed={0.06}>
      <section id="features" className="py-28 md:py-36 border-t border-white/[0.03] relative">
        <div className="max-w-6xl mx-auto px-6">
          <FadeInSection>
            <p className="text-xs tracking-[0.3em] text-white/20 mb-4 uppercase">Features</p>
            <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-20">
              Built for real job seekers
            </h2>
          </FadeInSection>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((feature, i) => (
              <FadeInSection key={feature.title} delay={i * 0.06}>
                <BentoCard feature={feature} index={i} />
              </FadeInSection>
            ))}
          </div>
        </div>      </section>
      </ParallaxSection>


      {/* ─── Marquee / Social Proof ─── */}
      <section className="py-12 border-y border-white/[0.03] overflow-hidden">
        <div className="flex animate-marquee whitespace-nowrap">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="flex items-center gap-12 mx-12">
              {['Google', 'Stripe', 'Notion', 'Vercel', 'Figma', 'Linear', 'Supabase', 'Railway', 'Cloudflare', 'Shopify'].map((name) => (
                <span key={`${i}-${name}`} className="text-sm font-medium text-white/10 tracking-wider uppercase">
                  {name}
                </span>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="py-32 md:py-40 relative">
        <FloatingOrbs count={3} className="opacity-40" />
        <div className="max-w-3xl mx-auto px-6 text-center relative z-10">
          <FadeInSection>
            <AnimatedBorder className="inline-block rounded-2xl" speed={2}>
              <div className="px-12 py-16 md:px-20 md:py-20 bg-black rounded-2xl">
                <motion.div
                  initial={{ scale: 0.95 }}
                  whileInView={{ scale: 1 }}
                  transition={{ duration: 0.5 }}
                >
                  <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
                    Your next opportunity<br />should find you.
                  </h2>
                  <p className="text-white/30 mb-10 max-w-lg mx-auto leading-relaxed">
                    Build your profile, get matched with relevant opportunities, and manage your entire job search in one place.
                  </p>
                  <MagneticButton
                    href="/signup"
                    className="btn-premium inline-flex items-center gap-2 bg-white text-black px-8 py-4 rounded-full font-semibold text-sm shadow-[0_0_60px_rgba(255,255,255,0.08)]"
                  >
                    Get Started Free
                    <ArrowRight size={16} />
                  </MagneticButton>
                </motion.div>
              </div>
            </AnimatedBorder>
          </FadeInSection>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-white/[0.03] py-12">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="text-lg font-bold tracking-tight mb-4">
                RO<span className="text-white/30">LIO</span>
              </div>
              <p className="text-xs text-white/20 leading-relaxed">
                Your career, intelligently matched.
              </p>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">Product</h4>
              <div className="space-y-2">
                <a href="#how-it-works" className="block text-sm text-white/20 hover:text-white/50 transition-colors">How It Works</a>
                <a href="#features" className="block text-sm text-white/20 hover:text-white/50 transition-colors">Features</a>
                <Link href="/jobs" className="block text-sm text-white/20 hover:text-white/50 transition-colors">Browse Jobs</Link>
              </div>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">Account</h4>
              <div className="space-y-2">
                <Link href="/login" className="block text-sm text-white/20 hover:text-white/50 transition-colors">Sign In</Link>
                <Link href="/signup" className="block text-sm text-white/20 hover:text-white/50 transition-colors">Sign Up</Link>
                <Link href="/profile" className="block text-sm text-white/20 hover:text-white/50 transition-colors">Profile</Link>
              </div>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">Legal</h4>
              <div className="space-y-2">
                <span className="block text-sm text-white/20">Privacy Policy</span>
                <span className="block text-sm text-white/20">Terms of Service</span>
              </div>
            </div>
          </div>
          <div className="border-t border-white/[0.03] pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-white/15">© 2026 Rolio. All rights reserved.</p>
            <p className="text-xs text-white/10">Built with intelligence</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
