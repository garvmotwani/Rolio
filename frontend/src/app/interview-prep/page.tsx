'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, apiGet, apiPost } from '@/lib/store';
import { apiStream } from '@/lib/api';
import Link from 'next/link';
import {
  Brain, Sparkles, ArrowRight, ChevronLeft, ChevronRight,
  Check, X, RotateCcw, Loader2, Briefcase, Code, Layers, Target
} from 'lucide-react';

interface Flashcard {
  question: string;
  answer: string;
  category: string;
  difficulty: string;
}

const CATEGORIES = [
  { value: 'all', label: 'All', icon: Target },
  { value: 'behavioral', label: 'Behavioral', icon: Brain },
  { value: 'technical', label: 'Technical', icon: Code },
  { value: 'system-design', label: 'System Design', icon: Layers },
];

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-emerald-500/10 text-emerald-400/70 border-emerald-500/20',
  medium: 'bg-amber-500/10 text-amber-400/70 border-amber-500/20',
  hard: 'bg-red-500/10 text-red-400/70 border-red-500/20',
};

export default function InterviewPrepPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#050505] flex items-center justify-center"><div className="text-white/40">Loading...</div></div>}>
      <InterviewPrepPage />
    </Suspense>
  );
}

function InterviewPrepPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');

  const [applications, setApplications] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [category, setCategory] = useState('all');
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  // Flashcard navigation
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewed, setReviewed] = useState<Record<number, 'correct' | 'skip'>>({});

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadApplications();
  }, [user, hydrated, router]);

  const loadApplications = async () => {
    try {
      const apps = await apiGet<any[]>('/api/applications');
      setApplications(apps);
      if (jobId) {
        const match = apps.find(a => a.job_id === parseInt(jobId));
        if (match) setSelectedJob(match);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setFetching(false);
    }
  };

  const [streamingText, setStreamingText] = useState('');

  const generate = async () => {
    if (!selectedJob || loading) return;
    setLoading(true);
    setCards([]);
    setCurrentIndex(0);
    setFlipped(false);
    setReviewed({});
    setStreamingText('');

    try {
      await apiStream('/api/interview-prep/generate/stream', { job_id: selectedJob.job_id, category, count: 10 }, {
        onToken: (token) => setStreamingText(prev => prev + token),
        onDone: (final) => {
          const payload = final as { cards?: Flashcard[] };
          setCards(payload?.cards || []);
          setStreamingText('');
        },
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const markReviewed = (type: 'correct' | 'skip') => {
    setReviewed(prev => ({ ...prev, [currentIndex]: type }));
    if (currentIndex < cards.length - 1) {
      setFlipped(false);
      setTimeout(() => setCurrentIndex(prev => prev + 1), 150);
    }
  };

  const reset = () => {
    setCurrentIndex(0);
    setFlipped(false);
    setReviewed({});
  };

  const progress = cards.length > 0 ? Object.keys(reviewed).length / cards.length : 0;
  const correctCount = Object.values(reviewed).filter(v => v === 'correct').length;

  if (!hydrated || !user) return null;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <Brain size={18} className="text-white/40" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Interview Prep</h1>
            <p className="text-white/25 text-sm">AI-generated flashcards tailored to each role</p>
          </div>
        </div>

        {cards.length === 0 && !loading ? (
          /* Setup View */
          <div className="max-w-lg mx-auto space-y-4">
            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-[13px] font-semibold mb-3">Select Application</h3>
              {fetching ? (
                <div className="skeleton h-10 rounded-lg" />
              ) : (
                <select
                  value={selectedJob?.job_id || ''}
                  onChange={(e) => {
                    const app = applications.find(a => a.job_id === parseInt(e.target.value));
                    setSelectedJob(app || null);
                  }}
                  className="w-full bg-[#0a0a0a] border border-white/[0.06] rounded-lg px-3 py-2.5 text-sm text-white/70 outline-none focus:border-white/[0.12] transition-colors appearance-none"
                >
                  <option value="">Choose a job...</option>
                  {applications.map(app => (
                    <option key={app.job_id} value={app.job_id}>
                      {app.job_title} @ {app.company_name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="bg-[#050505] border border-white/[0.04] rounded-xl p-5">
              <h3 className="text-[13px] font-semibold mb-3">Category</h3>
              <div className="grid grid-cols-2 gap-2">
                {CATEGORIES.map(c => (
                  <button
                    key={c.value}
                    onClick={() => setCategory(c.value)}
                    className={`flex items-center gap-2 p-3 rounded-lg border transition-all text-sm ${
                      category === c.value
                        ? 'bg-white/[0.06] border-white/[0.12] text-white/80'
                        : 'border-white/[0.04] text-white/40 hover:border-white/[0.08]'
                    }`}
                  >
                    <c.icon size={14} />
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={generate}
              disabled={!selectedJob}
              className="w-full bg-white text-black py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 hover:bg-white/90 transition-colors disabled:opacity-30 press-scale"
            >
              <Sparkles size={16} /> Generate Flashcards
            </button>
          </div>
        ) : loading ? (
          /* Loading with streaming text */
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 size={32} className="text-white/20 animate-spin mb-4" />
            <p className="text-sm text-white/30 mb-4">Generating interview questions...</p>
            {streamingText && (
              <div className="max-w-lg mx-auto bg-[#050505] border border-white/[0.04] rounded-xl p-5">
                <p className="text-xs text-white/20 uppercase tracking-wider mb-2">AI Response</p>
                <p className="text-sm text-white/40 font-mono leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {streamingText}
                  <span className="animate-pulse">|</span>
                </p>
              </div>
            )}
          </div>
        ) : (
          /* Flashcard View */
          <div className="max-w-2xl mx-auto">
            {/* Progress */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <span className="text-sm text-white/40">
                  {currentIndex + 1} / {cards.length}
                </span>
                <div className="w-32 h-1 bg-white/[0.04] rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-white/30 rounded-full"
                    animate={{ width: `${progress * 100}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
                {correctCount > 0 && (
                  <span className="text-xs text-emerald-400/60">{correctCount} correct</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={reset}
                  className="p-2 rounded-lg hover:bg-white/[0.05] transition-colors"
                  title="Reset"
                >
                  <RotateCcw size={14} className="text-white/30" />
                </button>
                <button
                  onClick={() => { setCards([]); setSelectedJob(null); }}
                  className="text-xs text-white/30 hover:text-white/50 transition-colors"
                >
                  New job
                </button>
              </div>
            </div>

            {/* Flashcard */}
            <div className="perspective-1000">
              <motion.div
                className={`relative w-full min-h-[350px] cursor-pointer rounded-2xl ${
                  flipped ? '' : ''
                }`}
                onClick={() => !flipped && setFlipped(true)}
                style={{ perspective: 1000 }}
              >
                <AnimatePresence mode="wait">
                  {!flipped ? (
                    <motion.div
                      key={`q-${currentIndex}`}
                      initial={{ opacity: 0, rotateY: -90 }}
                      animate={{ opacity: 1, rotateY: 0 }}
                      exit={{ opacity: 0, rotateY: 90 }}
                      transition={{ duration: 0.3 }}
                      className="absolute inset-0 bg-[#050505] border border-white/[0.06] rounded-2xl p-8 flex flex-col"
                    >
                      <div className="flex items-center gap-2 mb-6">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                          DIFFICULTY_COLORS[cards[currentIndex]?.difficulty] || DIFFICULTY_COLORS.medium
                        }`}>
                          {cards[currentIndex]?.difficulty}
                        </span>
                        <span className="text-[10px] text-white/20 capitalize">
                          {cards[currentIndex]?.category}
                        </span>
                      </div>
                      <div className="flex-1 flex items-center justify-center">
                        <h2 className="text-xl font-semibold text-white/80 text-center leading-relaxed">
                          {cards[currentIndex]?.question}
                        </h2>
                      </div>
                      <p className="text-xs text-white/15 text-center mt-4">Click to reveal answer</p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key={`a-${currentIndex}`}
                      initial={{ opacity: 0, rotateY: -90 }}
                      animate={{ opacity: 1, rotateY: 0 }}
                      exit={{ opacity: 0, rotateY: 90 }}
                      transition={{ duration: 0.3 }}
                      className="absolute inset-0 bg-[#050505] border border-white/[0.08] rounded-2xl p-8 flex flex-col"
                    >
                      <div className="flex items-center gap-2 mb-4">
                        <span className="text-[10px] text-white/30 uppercase tracking-wider">Answer</span>
                      </div>
                      <div className="flex-1 flex items-center">
                        <p className="text-sm text-white/60 leading-relaxed">
                          {cards[currentIndex]?.answer}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            </div>

            {/* Action Buttons */}
            {flipped && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-center gap-4 mt-6"
              >
                <button
                  onClick={() => markReviewed('skip')}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-sm text-white/40 hover:text-white/60 transition-all"
                >
                  <X size={16} /> Skip
                </button>
                <button
                  onClick={() => markReviewed('correct')}
                  className="flex items-center gap-2 px-8 py-3 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.08] text-sm text-white/70 hover:text-white/90 transition-all"
                >
                  <Check size={16} /> Got it
                </button>
              </motion.div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6">
              <button
                onClick={() => { if (currentIndex > 0) { setFlipped(false); setCurrentIndex(prev => prev - 1); } }}
                disabled={currentIndex === 0}
                className="p-2 rounded-lg hover:bg-white/[0.05] transition-colors disabled:opacity-20"
              >
                <ChevronLeft size={18} className="text-white/40" />
              </button>

              {/* Card indicators */}
              <div className="flex gap-1.5">
                {cards.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => { setFlipped(false); setCurrentIndex(i); }}
                    className={`w-2 h-2 rounded-full transition-all ${
                      i === currentIndex ? 'bg-white/40 scale-125' :
                      reviewed[i] === 'correct' ? 'bg-emerald-400/50' :
                      reviewed[i] === 'skip' ? 'bg-white/10' :
                      'bg-white/[0.08]'
                    }`}
                  />
                ))}
              </div>

              <button
                onClick={() => { if (currentIndex < cards.length - 1) { setFlipped(false); setCurrentIndex(prev => prev + 1); } }}
                disabled={currentIndex === cards.length - 1}
                className="p-2 rounded-lg hover:bg-white/[0.05] transition-colors disabled:opacity-20"
              >
                <ChevronRight size={18} className="text-white/40" />
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
