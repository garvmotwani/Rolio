'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, apiGet, apiPut } from '@/lib/store';
import { formatINR } from '@/lib/format';
import Link from 'next/link';
import {
  MapPin, DollarSign, IndianRupee, Calendar, Plus, Briefcase,
  CheckCircle2, Clock, XCircle, Send, Eye, GripVertical
} from 'lucide-react';
import {
  DndContext, DragOverlay, closestCorners, PointerSensor,
  useSensor, useSensors, DragStartEvent, DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, verticalListSortingStrategy, useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useToast } from '@/components/Toast';

interface KanbanCard {
  id: number;
  job_id: number;
  status: string;
  notes: string;
  applied_at: string | null;
  interview_date: string | null;
  updated_at: string | null;
  job_title: string;
  company_name: string;
  company_logo: string;
  location: string;
  salary_min: number;
  salary_max: number;
  match_score: number;
}

interface KanbanData {
  columns: Record<string, KanbanCard[]>;
  stats: Record<string, number>;
  stages: string[];
  total: number;
}

const STAGE_CONFIG: Record<string, { label: string; icon: any; color: string; dotColor: string; bgColor: string }> = {
  saved:     { label: 'Saved',       icon: Eye,          color: 'bg-white/[0.02]',   dotColor: 'bg-white/20',    bgColor: 'border-white/[0.04]' },
  applied:   { label: 'Applied',     icon: Send,         color: 'bg-blue-500/[0.03]', dotColor: 'bg-blue-400',    bgColor: 'border-blue-500/10' },
  screening: { label: 'Screening',   icon: Clock,        color: 'bg-amber-500/[0.03]',dotColor: 'bg-amber-400',   bgColor: 'border-amber-500/10' },
  interview: { label: 'Interview',   icon: Briefcase,    color: 'bg-emerald-500/[0.03]',dotColor: 'bg-emerald-400', bgColor: 'border-emerald-500/10' },
  offer:     { label: 'Offer',       icon: CheckCircle2, color: 'bg-green-500/[0.03]',dotColor: 'bg-green-400',   bgColor: 'border-green-500/10' },
  rejected:  { label: 'Rejected',    icon: XCircle,      color: 'bg-red-500/[0.03]', dotColor: 'bg-red-400',     bgColor: 'border-red-500/10' },
};

/* ─── Sortable Card ─── */
function SortableCard({ card }: { card: KanbanCard }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `card-${card.id}`,
    data: { card, type: 'card' },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div className={`bg-[#080808] border border-white/[0.04] hover:border-white/[0.08] rounded-xl p-3.5 group transition-all duration-200 relative ${isDragging ? 'shadow-2xl shadow-black/50 ring-1 ring-white/10' : ''}`}>
        {/* Drag handle */}
        <div {...listeners} className="absolute top-3 right-8 p-1 rounded opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing transition-opacity">
          <GripVertical size={12} className="text-white/20" />
        </div>

        {/* Match score badge */}
        {card.match_score > 0 && (
          <div className="absolute top-2.5 right-10">
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
              card.match_score >= 80 ? 'bg-white/10 text-white/70' :
              card.match_score >= 60 ? 'bg-white/[0.06] text-white/45' :
              'bg-white/[0.03] text-white/25'
            }`}>
              {Math.round(card.match_score)}%
            </span>
          </div>
        )}

        {/* Card content */}
        <Link href={`/jobs/${card.job_id}`} className="block">
          <div className="flex items-start gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center flex-shrink-0 overflow-hidden">
              {card.company_logo ? (
                <img src={card.company_logo} alt="" className="w-full h-full object-cover" />
              ) : (
                <span className="text-[10px] font-semibold text-white/30">{card.company_name?.[0]}</span>
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium text-white/80 truncate leading-tight">{card.job_title}</p>
              <p className="text-[11px] text-white/30 mt-0.5 truncate">{card.company_name}</p>
            </div>
          </div>
        </Link>

        <div className="mt-2.5 flex flex-wrap gap-2 text-[10px] text-white/20">
          {card.location && (
            <span className="flex items-center gap-0.5">
              <MapPin size={9} />{card.location.length > 18 ? card.location.slice(0, 18) + '...' : card.location}
            </span>
          )}
          {card.salary_min > 0 && (
            <span className="flex items-center gap-0.5">
              <IndianRupee size={9} />{formatINR(card.salary_min)}–{formatINR(card.salary_max)}
            </span>
          )}
        </div>

        {card.applied_at && (
          <p className="text-[9px] text-white/12 mt-1.5">{new Date(card.applied_at).toLocaleDateString()}</p>
        )}
        {card.interview_date && (
          <div className="mt-1.5 flex items-center gap-1 text-[10px] text-emerald-400/60">
            <Calendar size={9} />{new Date(card.interview_date).toLocaleDateString()}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Drag Overlay Card ─── */
function OverlayCard({ card }: { card: KanbanCard }) {
  return (
    <div className="bg-[#0a0a0a] border border-white/10 rounded-xl p-3.5 shadow-2xl shadow-black/60 ring-1 ring-white/10 w-[280px] rotate-2">
      <div className="flex items-start gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center flex-shrink-0 overflow-hidden">
          {card.company_logo ? (
            <img src={card.company_logo} alt="" className="w-full h-full object-cover" />
          ) : (
            <span className="text-[10px] font-semibold text-white/40">{card.company_name?.[0]}</span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium text-white/90 truncate leading-tight">{card.job_title}</p>
          <p className="text-[11px] text-white/40 mt-0.5 truncate">{card.company_name}</p>
        </div>
      </div>
    </div>
  );
}

/* ─── Droppable Column ─── */
function DroppableColumn({ stage, cards }: { stage: string; cards: KanbanCard[] }) {
  const config = STAGE_CONFIG[stage];
  const Icon = config.icon;

  return (
    <div className={`flex flex-col min-w-[280px] max-w-[300px] w-full flex-shrink-0 rounded-xl border ${config.bgColor} ${config.color}`}>
      {/* Column header */}
      <div className="flex items-center gap-2 px-4 pt-3.5 pb-2">
        <div className={`w-2 h-2 rounded-full ${config.dotColor}`} />
        <Icon size={12} className="text-white/25" />
        <span className="text-[11px] font-semibold text-white/50 uppercase tracking-wider">{config.label}</span>
        <span className="text-[10px] text-white/15 ml-auto bg-white/[0.04] px-2 py-0.5 rounded-full font-mono">{cards.length}</span>
      </div>

      {/* Droppable area */}
      <SortableContext items={cards.map(c => `card-${c.id}`)} strategy={verticalListSortingStrategy}>
        <div className="flex-1 space-y-2 px-2.5 pb-2.5 min-h-[120px]">
          {cards.map(card => (
            <SortableCard key={card.id} card={card} />
          ))}
          {cards.length === 0 && (
            <div className="flex items-center justify-center h-20 text-[11px] text-white/10 border border-dashed border-white/[0.04] rounded-lg">
              Drop here
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

/* ─── Main Page ─── */
export default function KanbanPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [data, setData] = useState<KanbanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCard, setActiveCard] = useState<KanbanCard | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { addToast } = useToast();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadBoard();
  }, [user, hydrated, router]);

  const loadBoard = async () => {
    try {
      const result = await apiGet<KanbanData>('/api/kanban');
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const findStageByCardId = (cardId: string): string | null => {
    const numId = parseInt(cardId.replace('card-', ''));
    if (!data) return null;
    for (const [stage, cards] of Object.entries(data.columns)) {
      if (cards.some(c => c.id === numId)) return stage;
    }
    return null;
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const cardId = String(active.id).replace('card-', '');
    if (!data) return;
    for (const cards of Object.values(data.columns)) {
      const found = cards.find(c => c.id === parseInt(cardId));
      if (found) { setActiveCard(found); break; }
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCard(null);
    if (!over || !data) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    const fromStage = findStageByCardId(activeId);
    // Check if dropped on another card or on a column
    let toStage = findStageByCardId(overId);
    if (!toStage) {
      // Dropped on an empty column — overId would be the stage name
      toStage = data.stages.find(s => s === overId) || null;
    }

    if (!fromStage || !toStage || fromStage === toStage) return;

    const numId = parseInt(activeId.replace('card-', ''));
    handleMove(numId, toStage);
  };

  const handleMove = async (appId: number, newStatus: string) => {
    if (!data) return;

    // Optimistic update
    setData(prev => {
      if (!prev) return prev;
      const newColumns = { ...prev.columns };
      let movedCard: KanbanCard | null = null;

      for (const stage of Object.keys(newColumns)) {
        const idx = newColumns[stage].findIndex(c => c.id === appId);
        if (idx !== -1) {
          movedCard = { ...newColumns[stage][idx], status: newStatus };
          newColumns[stage] = [...newColumns[stage].slice(0, idx), ...newColumns[stage].slice(idx + 1)];
          break;
        }
      }

      if (movedCard) {
        newColumns[newStatus] = [movedCard, ...newColumns[newStatus]];
      }

      const newStats: Record<string, number> = {};
      for (const stage of Object.keys(newColumns)) {
        newStats[stage] = newColumns[stage].length;
      }

      return { ...prev, columns: newColumns, stats: newStats };
    });

    addToast(`Moved to ${STAGE_CONFIG[newStatus]?.label || newStatus}`, 'success');

    try {
      await apiPut(`/api/kanban/${appId}/move`, { status: newStatus });
    } catch (err) {
      addToast('Failed to move — reverting', 'error');
      loadBoard();
    }
  };

  if (!hydrated || !user || loading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="space-y-6">
          <div className="skeleton h-10 w-60" />
          <div className="flex gap-4 overflow-hidden">
            {[1, 2, 3, 4].map(i => <div key={i} className="skeleton h-80 w-72 rounded-xl" />)}
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const activeStages = data.stages.filter(s => data.stats[s] > 0 || ['saved', 'applied', 'interview'].includes(s));

  return (
    <div className="max-w-full mx-auto px-6 py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Application Pipeline</h1>
            <p className="text-white/25 text-sm mt-1">
              Drag cards between columns to update status · {data.total} application{data.total !== 1 ? 's' : ''}
            </p>
          </div>
          <Link href="/jobs" className="flex items-center gap-2 bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.06] rounded-lg px-4 py-2 text-xs font-medium text-white/60 hover:text-white/80 transition-all">
            <Plus size={14} /> Find jobs
          </Link>
        </div>

        {/* Kanban Board */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div ref={scrollRef} className="flex gap-3 overflow-x-auto pb-6 scrollbar-thin">
            {activeStages.map(stage => (
              <DroppableColumn
                key={stage}
                stage={stage}
                cards={data.columns[stage] || []}
              />
            ))}
          </div>

          <DragOverlay>
            {activeCard ? <OverlayCard card={activeCard} /> : null}
          </DragOverlay>
        </DndContext>
      </motion.div>
    </div>
  );
}
