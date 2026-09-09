'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send, Sparkles, Bot, User, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/lib/store';
import { apiStream, apiPost } from '@/lib/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTIONS = [
  "What are my top job matches?",
  "How can I improve my profile?",
  "What skills should I add?",
  "Help me prep for interviews",
];

/**
 * Safely render markdown-formatted text as React elements.
 * Only supports **bold**, *italic*, `code`, and newlines.
 * All other HTML is escaped — no dangerouslySetInnerHTML.
 */
function SafeMarkdown({ text }: { text: string }) {
  const parts: Array<{ type: 'text' | 'bold' | 'italic' | 'code'; content: string }> = [];
  let remaining = text;
  const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }
    if (match[1]) {
      parts.push({ type: 'bold', content: match[2] });
    } else if (match[3]) {
      parts.push({ type: 'italic', content: match[4] });
    } else if (match[5]) {
      parts.push({ type: 'code', content: match[6] });
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) });
  }

  if (parts.length === 0 || (parts.length === 1 && parts[0].type === 'text')) {
    return (
      <>
        {text.split('\n').map((line, i, arr) => (
          <span key={i}>
            {line}
            {i < arr.length - 1 && <br />}
          </span>
        ))}
      </>
    );
  }

  return (
    <>
      {parts.map((part, i) => {
        switch (part.type) {
          case 'bold':
            return <strong key={i} className="font-semibold">{part.content}</strong>;
          case 'italic':
            return <em key={i}>{part.content}</em>;
          case 'code':
            return (
              <code key={i} className="bg-white/10 px-1 py-0.5 rounded text-[12px] font-mono">
                {part.content}
              </code>
            );
          default:
            return <span key={i}>{part.content}</span>;
        }
      })}
    </>
  );
}

export default function AIChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const user = useAuthStore(s => s.user);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading || !user) return;

    const userMsg: ChatMessage = { role: 'user', content: text.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setStreamingContent('');

    try {
      let fullContent = '';
      let streamed = false;

      // Try streaming first — tokens appear progressively
      await apiStream('/api/ai/chat/stream', {
        message: text.trim(),
        history: messages.slice(-10),
      }, {
        onToken: (token) => {
          streamed = true;
          fullContent += token;
          setStreamingContent(fullContent);
        },
        onDone: (final) => {
          const payload = final as { full?: string };
          setMessages(prev => [...prev, { role: 'assistant', content: payload?.full || fullContent }]);
          setStreamingContent('');
        },
      });

      // If the stream produced nothing (non-streaming fallback response),
      // fall back to the plain chat endpoint.
      if (!streamed) {
        const data = await apiPost<{ response?: string }>('/api/ai/chat', {
          message: text.trim(),
          history: messages.slice(-10),
        });
        setMessages(prev => [...prev, { role: 'assistant', content: data.response || 'No response' }]);
      }
    } catch {
      // Fallback to non-streaming on connection error
      try {
        const data = await apiPost<{ response?: string }>('/api/ai/chat', {
          message: text.trim(),
          history: messages.slice(-10),
        });
        setMessages(prev => [...prev, { role: 'assistant', content: data.response || 'Connection error. Please try again.' }]);
      } catch {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Please check your network and try again.' }]);
      }
    } finally {
      setIsLoading(false);
      setStreamingContent('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (!user) return null;

  return (
    <>
      {/* Floating button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-[9990] w-14 h-14 rounded-full bg-white text-black shadow-lg shadow-white/20 flex items-center justify-center hover:shadow-white/40 transition-shadow"
            aria-label="Open AI chat"
          >
            <MessageCircle size={22} />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed bottom-6 right-6 z-[9999] w-[400px] max-w-[calc(100vw-2rem)] h-[600px] max-h-[calc(100vh-3rem)] bg-[#0a0a0a] border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
            role="dialog"
            aria-label="AI Chat Assistant"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/[0.03]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  <Sparkles size={16} className="text-white/80" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white/90">Rolio AI</h3>
                  <p className="text-[10px] text-white/40">Career assistant</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="w-7 h-7 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/40 hover:text-white/80 transition-colors"
                aria-label="Close chat"
              >
                <X size={14} />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
              {messages.length === 0 && !streamingContent && (
                <div className="flex flex-col items-center justify-center h-full text-center px-4">
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.05] border border-white/10 flex items-center justify-center mb-4">
                    <Bot size={24} className="text-white/40" />
                  </div>
                  <p className="text-white/60 text-sm font-medium mb-1">Ask me anything</p>
                  <p className="text-white/30 text-xs mb-6">I know your profile, skills, and job matches</p>
                  <div className="grid grid-cols-2 gap-2 w-full">
                    {SUGGESTIONS.map((s, i) => (
                      <motion.button
                        key={i}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        onClick={() => sendMessage(s)}
                        className="text-left text-xs text-white/50 bg-white/[0.03] border border-white/5 rounded-xl px-3 py-2.5 hover:bg-white/[0.07] hover:text-white/70 hover:border-white/10 transition-all"
                      >
                        {s}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ type: 'spring', damping: 20 }}
                  className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles size={12} className="text-white/60" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-white text-black'
                        : 'bg-white/[0.05] text-white/80 border border-white/5'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">
                      <SafeMarkdown text={msg.content} />
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                      <User size={12} className="text-white/60" />
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Streaming message in progress */}
              {(streamingContent || isLoading && !streamingContent) && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-2.5"
                >
                  <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Sparkles size={12} className="text-white/60" />
                  </div>
                  <div className="bg-white/[0.05] border border-white/5 rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed text-white/80 max-w-[80%]">
                    {streamingContent ? (
                      <div className="whitespace-pre-wrap">
                        <SafeMarkdown text={streamingContent} />
                        <span className="inline-block w-1.5 h-3.5 bg-white/40 ml-0.5 animate-pulse rounded-sm" />
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Loader2 size={14} className="text-white/40 animate-spin" />
                        <span className="text-white/30 text-xs">Thinking...</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-white/5 bg-white/[0.02]">
              <div className="flex items-center gap-2 bg-white/[0.05] rounded-xl border border-white/5 px-3 py-2 focus-within:border-white/15 transition-colors">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Ask about your career..."
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  className="bg-transparent text-white/90 text-sm flex-1 outline-none placeholder:text-white/25 disabled:opacity-50"
                  aria-label="Chat message input"
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isLoading}
                  className="w-7 h-7 rounded-lg bg-white text-black flex items-center justify-center disabled:opacity-20 disabled:cursor-not-allowed hover:bg-white/90 transition-colors shrink-0"
                  aria-label="Send message"
                >
                  <Send size={13} />
                </button>
              </div>
              <p className="text-[10px] text-white/20 text-center mt-1.5">AI responses may be inaccurate. Verify important information.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
