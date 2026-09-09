'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, apiPost } from '@/lib/store';
import {
  Send, Bot, User, Sparkles, ArrowRight,
  Briefcase, Target, TrendingUp, MessageSquare, Loader2
} from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

const quickPrompts = [
  { icon: Target, label: 'What are my top job matches?', prompt: 'What are my top job matches and why?' },
  { icon: TrendingUp, label: 'How can I improve my profile?', prompt: 'How can I improve my profile strength?' },
  { icon: Briefcase, label: 'Application strategy tips', prompt: 'Give me tips on my application strategy' },
  { icon: Sparkles, label: 'Interview prep advice', prompt: 'Help me prepare for interviews' },
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

export default function AiChatPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
  }, [user, hydrated, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: text.trim(), timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await apiPost<{ response: string }>('/api/ai/chat', {
        message: text.trim(),
        history: messages.slice(-6).map(m => ({ role: m.role, content: m.content })),
      });

      const assistantMsg: Message = {
        role: 'assistant',
        content: result.response,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  if (!hydrated || !user) return null;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-80px)]">
      <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col h-full">
        {/* Header */}
        <motion.div variants={item} className="mb-6">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/[0.06] flex items-center justify-center">
              <Bot size={18} className="text-white/50" />
            </div>
            Career Assistant
          </h1>
          <p className="text-white/25 text-sm mt-1.5">Powered by Nemotron AI • Context-aware of your profile and matches</p>
        </motion.div>

        {/* Messages */}
        <motion.div variants={item} className="flex-1 overflow-y-auto space-y-4 mb-4 scrollbar-thin pr-1">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-5">
                <Sparkles size={28} className="text-white/20" />
              </div>
              <h2 className="text-lg font-semibold text-white/70 mb-2">Ask anything about your career</h2>
              <p className="text-sm text-white/25 max-w-md mb-8">
                I know your skills, experience, and job matches. Ask me for personalized career advice.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                {quickPrompts.map((qp, i) => (
                  <motion.button
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + i * 0.08 }}
                    onClick={() => sendMessage(qp.prompt)}
                    className="flex items-center gap-3 bg-[#050505] border border-white/[0.04] hover:border-white/[0.1] rounded-xl p-4 text-left transition-all duration-300 group press-scale"
                  >
                    <qp.icon size={16} className="text-white/20 group-hover:text-white/40 transition-colors flex-shrink-0" />
                    <span className="text-sm text-white/35 group-hover:text-white/60 transition-colors">{qp.label}</span>
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            <AnimatePresence mode="popLayout">
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot size={14} className="text-white/30" />
                    </div>
                  )}
                  <div className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-white/[0.08] border border-white/[0.06] text-white/90'
                      : 'bg-[#050505] border border-white/[0.04] text-white/70'
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-7 h-7 rounded-lg bg-white/[0.08] border border-white/[0.06] flex items-center justify-center flex-shrink-0 mt-1">
                      <User size={14} className="text-white/40" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
                <Bot size={14} className="text-white/30" />
              </div>
              <div className="bg-[#050505] border border-white/[0.04] rounded-xl px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-white/30">
                  <Loader2 size={14} className="animate-spin" />
                  Thinking...
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </motion.div>

        {/* Input */}
        <motion.div variants={item}>
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-center bg-[#050505] border border-white/[0.06] rounded-xl overflow-hidden focus-within:border-white/[0.12] transition-colors duration-300">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask about jobs, skills, interviews..."
                disabled={loading}
                className="flex-1 bg-transparent px-4 py-3.5 text-sm text-white/80 placeholder:text-white/20 outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="p-3 mr-1 rounded-lg hover:bg-white/[0.05] transition-colors disabled:opacity-20"
              >
                <Send size={16} className="text-white/40" />
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </div>
  );
}
