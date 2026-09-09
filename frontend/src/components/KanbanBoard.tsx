'use client';

import { useState, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion, AnimatePresence } from 'framer-motion';
import { GripVertical } from 'lucide-react';
import CompanyLogo from './CompanyLogo';

interface Application {
  id: number;
  job_id: number;
  status: string;
  notes: string;
  applied_at: string;
  match_score: number;
  job_title: string;
  company_name: string;
  company_logo: string;
  job_location: string;
  job_work_type: string;
  skills_required: string;
}

interface Column {
  key: string;
  label: string;
  dotColor: string;
}

const columns: Column[] = [
  { key: 'applied', label: 'Applied', dotColor: 'bg-white/40' },
  { key: 'screening', label: 'Screening', dotColor: 'bg-white/30' },
  { key: 'interview', label: 'Interview', dotColor: 'bg-white/60' },
  { key: 'offer', label: 'Offer', dotColor: 'bg-white/80' },
  { key: 'rejected', label: 'Rejected', dotColor: 'bg-white/15' },
];

interface KanbanBoardProps {
  applications: Application[];
  onStatusChange: (id: number, newStatus: string) => void;
  onCardClick?: (app: Application) => void;
}

function SortableCard({
  app,
  onCardClick,
}: {
  app: Application;
  onCardClick?: (app: Application) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: app.id,
    data: { type: 'card', status: app.status },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative bg-[#0a0a0a] border rounded-lg p-3 transition-all duration-200 cursor-grab active:cursor-grabbing ${
        isDragging
          ? 'opacity-40 border-white/20 scale-[0.98]'
          : 'border-white/[0.04] hover:border-white/[0.1] hover:bg-[#0c0c0c]'
      }`}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className="absolute top-3 right-2 p-1 text-white/0 group-hover:text-white/20 transition-colors"
      >
        <GripVertical size={12} />
      </div>

      {/* Card content */}
      <div
        className="cursor-pointer"
        onClick={() => onCardClick?.(app)}
      >
        <div className="flex items-start gap-2.5 pr-5">
          <CompanyLogo src={app.company_logo} name={app.company_name || ''} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate leading-tight">{app.job_title}</p>
            <p className="text-[11px] text-white/30 mt-0.5 truncate">{app.company_name}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2.5">
          {app.job_location && (
            <span className="text-[10px] text-white/20 bg-white/[0.03] px-1.5 py-0.5 rounded">
              {app.job_location}
            </span>
          )}
          {app.match_score > 0 && (
            <span className="text-[10px] text-white/25 font-mono ml-auto">
              {Math.round(app.match_score)}%
            </span>
          )}
        </div>

        <p className="text-[10px] text-white/15 mt-2">
          {new Date(app.applied_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
        </p>
      </div>
    </div>
  );
}

function OverlayCard({ app }: { app: Application }) {
  return (
    <div className="bg-[#0a0a0a] border border-white/20 rounded-lg p-3 shadow-2xl shadow-black/50 w-[220px] rotate-2">
      <div className="flex items-start gap-2.5">
        <CompanyLogo src={app.company_logo} name={app.company_name || ''} size="sm" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium truncate">{app.job_title}</p>
          <p className="text-[11px] text-white/30 mt-0.5 truncate">{app.company_name}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-2">
        {app.job_location && (
          <span className="text-[10px] text-white/30 bg-white/[0.06] px-1.5 py-0.5 rounded">
            {app.job_location}
          </span>
        )}
        {app.match_score > 0 && (
          <span className="text-[10px] text-white/40 font-mono ml-auto">
            {Math.round(app.match_score)}%
          </span>
        )}
      </div>
    </div>
  );
}

export default function KanbanBoard({ applications, onStatusChange, onCardClick }: KanbanBoardProps) {
  // Group applications by status
  const [items, setItems] = useState<Record<string, Application[]>>(() => {
    const grouped: Record<string, Application[]> = {};
    columns.forEach((col) => { grouped[col.key] = []; });
    applications.forEach((app) => {
      const key = app.status;
      if (grouped[key]) grouped[key].push(app);
    });
    return grouped;
  });

  const [activeId, setActiveId] = useState<number | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor),
  );

  const findColumn = useCallback((id: number | string): string | null => {
    // Check which column the item is in
    for (const [key, apps] of Object.entries(items)) {
      if (apps.some((a) => a.id === id)) return key;
    }
    // Might be dragging over a column directly
    if (typeof id === 'string' && columns.some((c) => c.key === id)) return id;
    return null;
  }, [items]);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(Number(event.active.id));
  }, []);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeCol = findColumn(active.id);
    const overCol = findColumn(over.id);

    if (!activeCol || !overCol || activeCol === overCol) return;

    setItems((prev) => {
      const activeItems = [...prev[activeCol]];
      const overItems = [...prev[overCol]];
      const activeIndex = activeItems.findIndex((a) => a.id === active.id);
      if (activeIndex === -1) return prev;

      const [moved] = activeItems.splice(activeIndex, 1);
      // Update status in-memory
      moved.status = overCol;

      const overIndex = overItems.findIndex((a) => a.id === over.id);
      if (overIndex >= 0) {
        overItems.splice(overIndex, 0, moved);
      } else {
        overItems.push(moved);
      }

      return { ...prev, [activeCol]: activeItems, [overCol]: overItems };
    });
  }, [findColumn]);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeCol = findColumn(active.id);
    const overCol = findColumn(over.id);

    if (!activeCol || !overCol) return;

    // Same column reorder
    if (activeCol === overCol) {
      setItems((prev) => {
        const col = [...prev[activeCol]];
        const oldIndex = col.findIndex((a) => a.id === active.id);
        const newIndex = col.findIndex((a) => a.id === over.id);
        if (oldIndex === -1 || newIndex === -1) return prev;
        return { ...prev, [activeCol]: arrayMove(col, oldIndex, newIndex) };
      });
      return;
    }

    // Cross-column: persist the status change
    const newStatus = overCol;
    onStatusChange(Number(active.id), newStatus);
  }, [findColumn, onStatusChange]);

  const activeApp = activeId
    ? Object.values(items).flat().find((a) => a.id === activeId)
    : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4 -mx-2 px-2">
        {columns.map((col) => {
          const colItems = items[col.key] || [];
          return (
            <div
              key={col.key}
              className="flex-shrink-0 w-[260px] flex flex-col"
            >
              {/* Column header */}
              <div className="flex items-center gap-2 mb-3 px-1">
                <span className={`w-1.5 h-1.5 rounded-full ${col.dotColor}`} />
                <span className="text-[11px] font-medium uppercase tracking-wider text-white/40">
                  {col.label}
                </span>
                <span className="text-[10px] text-white/15 font-mono ml-auto">
                  {colItems.length}
                </span>
              </div>

              {/* Drop zone */}
              <SortableContext items={colItems.map((a) => a.id)} strategy={verticalListSortingStrategy}>
                <div
                  className={`flex-1 min-h-[120px] rounded-xl p-2 space-y-2 transition-colors duration-200 ${
                    activeId
                      ? 'bg-white/[0.015] border border-dashed border-white/[0.06]'
                      : 'bg-transparent'
                  }`}
                >
                  <AnimatePresence>
                    {colItems.map((app) => (
                      <motion.div
                        key={app.id}
                        layout
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                      >
                        <SortableCard app={app} onCardClick={onCardClick} />
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {colItems.length === 0 && !activeId && (
                    <div className="flex items-center justify-center h-24 rounded-lg border border-dashed border-white/[0.04]">
                      <p className="text-[10px] text-white/12">Drop here</p>
                    </div>
                  )}
                </div>
              </SortableContext>
            </div>
          );
        })}
      </div>

      {/* Drag overlay (follows cursor, high z-index) */}
      <DragOverlay>
        {activeApp ? <OverlayCard app={activeApp} /> : null}
      </DragOverlay>
    </DndContext>
  );
}
