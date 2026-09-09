'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore, apiGet, apiPut, apiDelete, apiPost } from '@/lib/store';
import { apiDownload } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText, ExternalLink, Trash2, Edit3, X, Check, ArrowRight,
  Mail, Clock, Calendar, Bell, MessageSquare, ChevronDown, ChevronUp,
  ArrowUpRight, User, Send, Inbox, Plus, Sparkles, Download
} from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import CompanyLogo from '@/components/CompanyLogo';
import TiltCard from '@/components/TiltCard';
import AnimatedStatusPill from '@/components/AnimatedStatusPill';
import ParallaxSection from '@/components/ParallaxSection';

interface Application {
  id: number;
  job_id: number;
  status: string;
  notes: string;
  applied_at: string;
  interview_date: string | null;
  external_url: string;
  match_score: number;
  job_title: string;
  company_name: string;
  company_logo: string;
  job_location: string;
  job_work_type: string;
  skills_required: string;
}

interface AppEvent {
  id: number;
  event_type: string;
  title: string;
  description: string;
  old_value: string;
  new_value: string;
  created_at: string;
  email?: {
    subject: string;
    sender: string;
    received_at: string;
    snippet: string;
  };
}

interface AppReminder {
  id: number;
  title: string;
  message: string;
  remind_at: string;
  is_completed: boolean;
}

const statusGroups = [
  { key: 'applied', label: 'Applied', color: 'bg-white/10', dotColor: 'bg-white/40' },
  { key: 'screening', label: 'Screening', color: 'bg-white/8', dotColor: 'bg-white/30' },
  { key: 'interview', label: 'Interview', color: 'bg-white/15', dotColor: 'bg-white/60' },
  { key: 'offer', label: 'Offer', color: 'bg-white/20', dotColor: 'bg-white/80' },
  { key: 'rejected', label: 'Rejected', color: 'bg-white/5', dotColor: 'bg-white/15' },
  { key: 'withdrawn', label: 'Withdrawn', color: 'bg-white/3', dotColor: 'bg-white/10' },
];

const statusOptions = ['applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn'];

const eventTypeIcons: Record<string, any> = {
  status_change: ArrowUpRight,
  note_added: MessageSquare,
  email_received: Mail,
  interview_scheduled: Calendar,
  reminder_set: Bell,
  applied: Send,
};

export default function ApplicationsPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [events, setEvents] = useState<Record<number, AppEvent[]>>({});
  const [reminders, setReminders] = useState<Record<number, AppReminder[]>>({});
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState('');
  const [noteText, setNoteText] = useState('');
  const [addNoteId, setAddNoteId] = useState<number | null>(null);
  const [reminderDate, setReminderDate] = useState('');
  const [addReminderId, setAddReminderId] = useState<number | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadApplications();
  }, [user, hydrated, router]);

  const loadApplications = async () => {
    try {
      const data = await apiGet<Application[]>(`/api/applications?status=${filter}`);
      setApplications(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadApplications(); }, [filter]);

  const loadEvents = async (appId: number) => {
    if (events[appId]) return;
    try {
      const data = await apiGet<AppEvent[]>(`/api/gmail/applications/${appId}/events`);
      setEvents(prev => ({ ...prev, [appId]: data }));
    } catch (err) {
      console.error(err);
    }
  };

  const loadReminders = async (appId: number) => {
    if (reminders[appId]) return;
    try {
      const data = await apiGet<AppReminder[]>(`/api/gmail/applications/${appId}/reminders`);
      setReminders(prev => ({ ...prev, [appId]: data }));
    } catch (err) {
      console.error(err);
    }
  };

  const toggleExpand = async (appId: number) => {
    if (expandedId === appId) {
      setExpandedId(null);
    } else {
      setExpandedId(appId);
      await Promise.all([loadEvents(appId), loadReminders(appId)]);
    }
  };

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await apiPut(`/api/applications/${id}`, { status: newStatus });
      // Create event
      await apiPost(`/api/gmail/applications/${id}/events`, {
        event_type: 'status_change',
        title: 'Status changed manually',
        new_value: newStatus,
      });
      setEditingId(null);
      loadApplications();
      // Refresh events
      setEvents(prev => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
      loadEvents(id);
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiDelete(`/api/applications/${id}`);
      loadApplications();
    } catch (err) { console.error(err); }
  };

  const handleAddNote = async (appId: number) => {
    if (!noteText.trim()) return;
    try {
      await apiPost(`/api/gmail/applications/${appId}/events`, {
        event_type: 'note_added',
        title: 'Note added',
        description: noteText.trim(),
      });
      setNoteText('');
      setAddNoteId(null);
      // Refresh events
      setEvents(prev => {
        const copy = { ...prev };
        delete copy[appId];
        return copy;
      });
      loadEvents(appId);
    } catch (err) { console.error(err); }
  };

  const handleAddReminder = async (appId: number) => {
    if (!reminderDate) return;
    try {
      await apiPost(`/api/gmail/applications/${appId}/reminders`, {
        title: 'Follow up',
        message: `Follow up on application`,
        remind_at: new Date(reminderDate).toISOString(),
      });
      setReminderDate('');
      setAddReminderId(null);
      setReminders(prev => {
        const copy = { ...prev };
        delete copy[appId];
        return copy;
      });
      loadReminders(appId);
    } catch (err) { console.error(err); }
  };

  const grouped = statusGroups.map((sg) => ({
    ...sg,
    items: applications.filter((a) => sg.key === a.status),
  })).filter((g) => filter === 'all' || g.key === filter);

  const hasApps = applications.length > 0;

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="space-y-6">
          <div className="skeleton h-10 w-48" />
          <div className="flex gap-2 mb-6">
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-8 w-24 rounded-full" />)}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="space-y-3">
                <div className="skeleton h-6 w-24" />
                <div className="skeleton h-20 rounded-lg" />
                <div className="skeleton h-20 rounded-lg" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-15" />

      <div className="relative z-10">
        <ParallaxSection speed={0.06} className="mb-8">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Applications</h1>
                <p className="text-white/30 text-sm mt-1">
                  {applications.length} total application{applications.length !== 1 ? 's' : ''}
                </p>
              </div>
            <div className="flex items-center gap-3">
              <button
                onClick={async () => {
                  setExporting(true);
                  try {
                    await apiDownload(
                      '/api/export/applications',
                      `applications-${new Date().toISOString().split('T')[0]}.csv`
                    );
                  } catch (err) {
                    console.error('Export failed:', err);
                  } finally {
                    setExporting(false);
                  }
                }}
                disabled={exporting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-white/40 hover:text-white/60 hover:bg-white/[0.06] transition-all disabled:opacity-50"
              >
                <Download size={12} className={exporting ? 'animate-bounce' : ''} />
                {exporting ? 'Exporting...' : 'Export CSV'}
              </button>
              <Link
                href="/settings"
                className="flex items-center gap-1.5 text-xs text-white/30 hover:text-white/50 transition-colors"
              >
                <Mail size={14} />
                Gmail sync
              </Link>
            </div>
          </div>
        </motion.div>
        </ParallaxSection>

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setFilter('all')}
            className={`px-3.5 py-1.5 rounded-full text-xs transition-all duration-300 ${
              filter === 'all' ? 'bg-white text-black font-medium' : 'bg-white/[0.04] text-white/35 hover:text-white/55 hover:bg-white/[0.06]'
            }`}
          >
            All ({applications.length})
          </button>
          {statusGroups.map((sg) => {
            const count = applications.filter((a) => a.status === sg.key).length;
            if (count === 0 && filter !== sg.key) return null;
            return (
              <button
                key={sg.key}
                onClick={() => setFilter(sg.key)}
                className={`px-3.5 py-1.5 rounded-full text-xs capitalize transition-all duration-300 ${
                  filter === sg.key ? 'bg-white text-black font-medium' : 'bg-white/[0.04] text-white/35 hover:text-white/55 hover:bg-white/[0.06]'
                }`}
              >
                {sg.label} ({count})
              </button>
            );
          })}
        </div>

        {!hasApps ? (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center py-24">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mx-auto mb-5">
              <FileText size={28} className="text-white/10" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No applications yet</h3>
            <p className="text-white/25 text-sm max-w-sm mx-auto leading-relaxed mb-6">
              Browse matched jobs and start applying to track your progress here.
            </p>
            <Link href="/jobs" className="btn-premium inline-flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-full text-sm font-medium">
              Browse jobs <ArrowRight size={14} />
            </Link>
          </motion.div>
        ) : (
          /* ─── Application Cards with Timeline ─── */
          <div className="space-y-3">
            <AnimatePresence>
              {applications.map((app, i) => {
                const isExpanded = expandedId === app.id;
                const appEvents = events[app.id] || [];
                const appReminders = reminders[app.id] || [];
                const sg = statusGroups.find(s => s.key === app.status);

                return (
                  <motion.div
                    key={app.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <div className="bg-[#050505] border border-white/[0.04] hover:border-white/[0.08] rounded-xl overflow-hidden transition-all duration-300">
                      {/* Main row */}
                      <div className="p-4">
                        <div className="flex items-center gap-3">
                          <CompanyLogo src={app.company_logo} name={app.company_name || ''} size="md" />
                          <div className="flex-1 min-w-0">
                            <Link href={`/jobs/${app.job_id}`} className="font-medium text-sm hover:text-white/80 transition-colors">
                              {app.job_title}
                            </Link>
                            <div className="flex items-center gap-2 mt-0.5">
                              <p className="text-xs text-white/30">{app.company_name}</p>
                              {app.job_location && (
                                <span className="text-[10px] text-white/15">· {app.job_location}</span>
                              )}
                            </div>
                          </div>

                          {/* Status badge */}
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {editingId === app.id ? (
                              <div className="flex items-center gap-1">
                                <select
                                  value={editStatus}
                                  onChange={(e) => setEditStatus(e.target.value)}
                                  className="text-[11px] py-1 px-2 bg-white/[0.04] border border-white/[0.06] rounded-lg"
                                >
                                  {statusOptions.map((s) => <option key={s} value={s}>{s}</option>)}
                                </select>
                                <button onClick={() => handleStatusChange(app.id, editStatus)} className="text-green-400 hover:text-green-300 p-1">
                                  <Check size={14} />
                                </button>
                                <button onClick={() => setEditingId(null)} className="text-white/30 hover:text-white/60 p-1">
                                  <X size={14} />
                                </button>
                              </div>
                            ) : (
                              <>
                                <AnimatedStatusPill status={app.status} />
                                {app.match_score > 0 && (
                                  <span className="text-[10px] font-mono text-white/20">{Math.round(app.match_score)}%</span>
                                )}
                              </>
                            )}
                          </div>
                        </div>

                        {/* Action buttons row */}
                        <div className="flex items-center gap-1 mt-3 pt-2 border-t border-white/[0.03]">
                          <span className="text-[10px] text-white/15 mr-auto">
                            Applied {new Date(app.applied_at).toLocaleDateString()}
                          </span>
                          <button
                            onClick={() => toggleExpand(app.id)}
                            className="flex items-center gap-1 text-[11px] text-white/25 hover:text-white/50 transition-colors px-2 py-1 rounded-lg hover:bg-white/[0.03]"
                          >
                            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            Timeline {appEvents.length > 0 && <span className="text-[9px] text-white/15">({appEvents.length})</span>}
                          </button>
                          <button
                            onClick={() => { setEditingId(app.id); setEditStatus(app.status); }}
                            className="p-1.5 text-white/15 hover:text-white/40 transition-colors rounded-lg hover:bg-white/[0.03]"
                          >
                            <Edit3 size={12} />
                          </button>
                          <button
                            onClick={() => setAddNoteId(app.id)}
                            className="p-1.5 text-white/15 hover:text-white/40 transition-colors rounded-lg hover:bg-white/[0.03]"
                            title="Add note"
                          >
                            <MessageSquare size={12} />
                          </button>
                          <button
                            onClick={() => setAddReminderId(app.id)}
                            className="p-1.5 text-white/15 hover:text-white/40 transition-colors rounded-lg hover:bg-white/[0.03]"
                            title="Set reminder"
                          >
                            <Bell size={12} />
                          </button>
                          {app.external_url && (
                            <a
                              href={app.external_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 text-white/15 hover:text-white/40 transition-colors rounded-lg hover:bg-white/[0.03]"
                            >
                              <ExternalLink size={12} />
                            </a>
                          )}
                          <button
                            onClick={() => handleDelete(app.id)}
                            className="p-1.5 text-white/15 hover:text-red-400 transition-colors rounded-lg hover:bg-white/[0.03]"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>

                      {/* Expanded: Timeline + Note Input + Reminders */}
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3 }}
                            className="overflow-hidden"
                          >
                            <div className="px-4 pb-4 border-t border-white/[0.03]">
                              {/* Add Note Input */}
                              {addNoteId === app.id && (
                                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="pt-3 pb-2">
                                  <div className="flex gap-2">
                                    <input
                                      type="text"
                                      value={noteText}
                                      onChange={(e) => setNoteText(e.target.value)}
                                      placeholder="Add a note..."
                                      className="flex-1 text-xs py-2 px-3 bg-white/[0.03] border border-white/[0.06] rounded-lg placeholder:text-white/15"
                                      onKeyDown={(e) => e.key === 'Enter' && handleAddNote(app.id)}
                                    />
                                    <button
                                      onClick={() => handleAddNote(app.id)}
                                      className="px-3 py-2 bg-white/[0.06] hover:bg-white/[0.1] rounded-lg text-xs transition-colors"
                                    >
                                      <Send size={12} />
                                    </button>
                                    <button
                                      onClick={() => { setAddNoteId(null); setNoteText(''); }}
                                      className="px-2 py-2 text-white/20 hover:text-white/40 transition-colors"
                                    >
                                      <X size={12} />
                                    </button>
                                  </div>
                                </motion.div>
                              )}

                              {/* Add Reminder Input */}
                              {addReminderId === app.id && (
                                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="pt-3 pb-2">
                                  <div className="flex gap-2">
                                    <input
                                      type="datetime-local"
                                      value={reminderDate}
                                      onChange={(e) => setReminderDate(e.target.value)}
                                      className="flex-1 text-xs py-2 px-3 bg-white/[0.03] border border-white/[0.06] rounded-lg"
                                    />
                                    <button
                                      onClick={() => handleAddReminder(app.id)}
                                      className="px-3 py-2 bg-white/[0.06] hover:bg-white/[0.1] rounded-lg text-xs transition-colors flex items-center gap-1"
                                    >
                                      <Bell size={12} /> Set
                                    </button>
                                    <button
                                      onClick={() => { setAddReminderId(null); setReminderDate(''); }}
                                      className="px-2 py-2 text-white/20 hover:text-white/40 transition-colors"
                                    >
                                      <X size={12} />
                                    </button>
                                  </div>
                                </motion.div>
                              )}

                              {/* Reminders */}
                              {appReminders.filter(r => !r.is_completed).length > 0 && (
                                <div className="pt-3">
                                  <p className="text-[10px] uppercase tracking-wider text-white/20 mb-2 flex items-center gap-1">
                                    <Bell size={10} /> Reminders
                                  </p>
                                  {appReminders.filter(r => !r.is_completed).map(reminder => (
                                    <div key={reminder.id} className="flex items-center gap-2 py-1.5 text-xs text-white/35">
                                      <Clock size={10} className="text-white/20" />
                                      <span>{reminder.title}</span>
                                      <span className="text-white/15">·</span>
                                      <span className="text-white/20">
                                        {new Date(reminder.remind_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Timeline */}
                              <div className="pt-3">
                                <p className="text-[10px] uppercase tracking-wider text-white/20 mb-3 flex items-center gap-1">
                                  <Clock size={10} /> Timeline
                                </p>
                                {appEvents.length === 0 ? (
                                  <p className="text-[11px] text-white/15 py-2">No events yet</p>
                                ) : (
                                  <div className="space-y-0 relative ml-1">
                                    {/* Vertical line */}
                                    <div className="absolute left-[5px] top-2 bottom-2 w-px bg-white/[0.04]" />

                                    {appEvents.map((event, ei) => {
                                      const Icon = eventTypeIcons[event.event_type] || Clock;
                                      const isEmail = event.event_type === 'email_received';
                                      return (
                                        <motion.div
                                          key={event.id}
                                          initial={{ opacity: 0, x: -5 }}
                                          animate={{ opacity: 1, x: 0 }}
                                          transition={{ delay: ei * 0.04 }}
                                          className="flex items-start gap-2.5 py-2 relative"
                                        >
                                          <div className={`w-[11px] h-[11px] rounded-full border flex-shrink-0 mt-0.5 z-10 flex items-center justify-center ${
                                            isEmail ? 'bg-blue-400/20 border-blue-400/30' :
                                            event.event_type === 'status_change' ? 'bg-white/[0.08] border-white/[0.15]' :
                                            event.event_type === 'note_added' ? 'bg-white/[0.06] border-white/[0.1]' :
                                            'bg-white/[0.04] border-white/[0.08]'
                                          }`}>
                                            <Icon size={6} className={isEmail ? 'text-blue-400/60' : 'text-white/30'} />
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            <p className="text-[11px] text-white/50 leading-tight">{event.title}</p>
                                            {event.description && (
                                              <p className="text-[10px] text-white/20 mt-0.5 leading-relaxed truncate">{event.description}</p>
                                            )}
                                            {event.old_value && event.new_value && (
                                              <p className="text-[10px] text-white/15 mt-0.5">
                                                {event.old_value} → {event.new_value}
                                              </p>
                                            )}
                                            {event.email && (
                                              <div className="mt-1 text-[10px] text-white/15 bg-white/[0.02] rounded px-2 py-1">
                                                <span className="text-blue-400/40">📧</span> {event.email.sender} — {event.email.subject?.slice(0, 60)}
                                              </div>
                                            )}
                                          </div>
                                          <span className="text-[9px] text-white/10 flex-shrink-0 mt-0.5">
                                            {formatTimeAgo(event.created_at)}
                                          </span>
                                        </motion.div>
                                      );
                                    })}
                                  </div>
                                )}
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
