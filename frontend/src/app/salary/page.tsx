'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuthStore, apiGet } from '@/lib/store';
import { formatINR } from '@/lib/format';
import {
  IndianRupee, TrendingUp, MapPin, BarChart3,
  ArrowUpRight, ArrowDownRight
} from 'lucide-react';

interface RoleBenchmark {
  junior: { min: number; max: number; median: number };
  mid: { min: number; max: number; median: number };
  senior: { min: number; max: number; median: number };
  lead: { min: number; max: number; median: number };
}

interface LocationData {
  name: string;
  multiplier: number;
}

const ROLE_OPTIONS = [
  'Software Engineer', 'Frontend Developer', 'Backend Developer',
  'Data Scientist', 'DevOps Engineer', 'Product Manager', 'UX Designer', 'ML Engineer',
];

const LEVELS: (keyof RoleBenchmark)[] = ['junior', 'mid', 'senior', 'lead'];
const LEVEL_COLORS: Record<string, string> = {
  junior: 'bg-blue-500',
  mid: 'bg-white/40',
  senior: 'bg-amber-500',
  lead: 'bg-purple-500',
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

function formatSalary(n: number) {
  // All benchmarks are annual INR — show as ₹NN L (lakhs per annum)
  return formatINR(n);
}

function SalaryBar({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-white/25 w-14 text-right">{label}</span>
      <div className="flex-1 h-3 bg-white/[0.03] rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(value / max) * 100}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className={`h-full ${color} rounded-full`}
        />
      </div>
      <span className="text-xs text-white/40 w-12">{formatSalary(value)}</span>
    </div>
  );
}

export default function SalaryPage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [selectedRole, setSelectedRole] = useState('Software Engineer');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [benchmarks, setBenchmarks] = useState<Record<string, RoleBenchmark>>({});
  const [locations, setLocations] = useState<LocationData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadLocations();
  }, [user, hydrated, router]);

  useEffect(() => {
    if (hydrated && user) loadBenchmarks();
  }, [selectedRole, selectedLocation, hydrated, user]);

  const loadLocations = async () => {
    try {
      const result = await apiGet<{ locations: LocationData[] }>('/api/salary/locations');
      setLocations(result.locations);
    } catch (err) {
      console.error(err);
    }
  };

  const loadBenchmarks = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ role: selectedRole });
      if (selectedLocation) params.set('location', selectedLocation);
      const result = await apiGet<{ roles?: Record<string, RoleBenchmark> }>(`/api/salary/benchmarks?${params}`);
      setBenchmarks(result.roles || {} as Record<string, RoleBenchmark>);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!hydrated || !user) return null;

  const roleData = benchmarks[selectedRole];
  const maxSalary = roleData ? Math.max(...LEVELS.map(l => roleData[l]?.max || 0)) : 200000;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <motion.div variants={container} initial="hidden" animate="show">
        {/* Header */}
        <motion.div variants={item} className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
              <IndianRupee size={18} className="text-white/40" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Salary Analytics</h1>
              <p className="text-white/25 text-sm">Compensation benchmarks across roles and cities (India, annual INR)</p>
            </div>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div variants={item} className="flex flex-wrap gap-3 mb-8">
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="bg-[#050505] border border-white/[0.06] rounded-lg px-4 py-2.5 text-sm text-white/70 outline-none focus:border-white/[0.12] transition-colors appearance-none"
          >
            {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value)}
            className="bg-[#050505] border border-white/[0.06] rounded-lg px-4 py-2.5 text-sm text-white/70 outline-none focus:border-white/[0.12] transition-colors appearance-none"
          >
            <option value="">India Average</option>
            {locations.map(l => (
              <option key={l.name} value={l.name}>
                {l.name} ({l.multiplier > 1 ? '+' : ''}{Math.round((l.multiplier - 1) * 100)}%)
              </option>
            ))}
          </select>
        </motion.div>

        {/* Main Chart */}
        {roleData && (
          <motion.div variants={item} className="bg-[#050505] border border-white/[0.04] rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-base font-semibold">{selectedRole}</h2>
              <span className="text-xs text-white/25">
                {selectedLocation || 'India Average'} · annual CTC
              </span>
            </div>

            <div className="space-y-5">
              {LEVELS.map(level => (
                <div key={level}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-white/50 capitalize">{level}</span>
                    <span className="text-[11px] text-white/20">
                      {formatSalary(roleData[level].min)} – {formatSalary(roleData[level].max)}
                    </span>
                  </div>
                  <div className="relative">
                    {/* Full range bar */}
                    <div className="h-8 bg-white/[0.02] rounded-lg overflow-hidden relative">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(roleData[level].max / maxSalary) * 100}%` }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        className="absolute top-0 left-0 h-full bg-white/[0.04] rounded-lg"
                      />
                      {/* Median marker */}
                      <motion.div
                        initial={{ left: 0 }}
                        animate={{ left: `${(roleData[level].median / maxSalary) * 100}%` }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        className="absolute top-0 h-full w-0.5 bg-white/40"
                      />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[10px] text-white/15">{formatSalary(roleData[level].min)}</span>
                      <span className="text-[10px] text-white/30 font-medium">Median: {formatSalary(roleData[level].median)}</span>
                      <span className="text-[10px] text-white/15">{formatSalary(roleData[level].max)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Cross-role comparison */}
        <motion.div variants={item} className="bg-[#050505] border border-white/[0.04] rounded-xl p-6">
          <h2 className="text-base font-semibold mb-6">Role Comparison (Mid-Level Median)</h2>
          <div className="space-y-3">
            {Object.entries(benchmarks)
              .sort((a, b) => (b[1].mid?.median || 0) - (a[1].mid?.median || 0))
              .map(([role, data]) => (
                <div key={role} className="flex items-center gap-3">
                  <span className="text-xs text-white/40 w-40 truncate">{role}</span>
                  <div className="flex-1 h-3 bg-white/[0.03] rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${((data.mid?.median || 0) / maxSalary) * 100}%` }}
                      transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="h-full bg-white/20 rounded-full"
                    />
                  </div>
                  <span className="text-xs text-white/50 w-14 text-right">{formatSalary(data.mid?.median || 0)}</span>
                </div>
              ))}
          </div>
        </motion.div>

        {/* Location Multipliers */}
        {locations.length > 0 && (
          <motion.div variants={item} className="bg-[#050505] border border-white/[0.04] rounded-xl p-6 mt-6">
            <h2 className="text-base font-semibold mb-4">Location Cost Multipliers</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {locations.map(loc => (
                <div
                  key={loc.name}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    selectedLocation === loc.name
                      ? 'bg-white/[0.06] border-white/[0.12]'
                      : 'bg-transparent border-white/[0.04] hover:border-white/[0.08]'
                  }`}
                  onClick={() => setSelectedLocation(selectedLocation === loc.name ? '' : loc.name)}
                >
                  <div className="flex items-center gap-1 mb-1">
                    <MapPin size={10} className="text-white/20" />
                    <span className="text-[11px] text-white/40 truncate">{loc.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {loc.multiplier > 1 ? (
                      <ArrowUpRight size={10} className="text-emerald-400/60" />
                    ) : loc.multiplier < 1 ? (
                      <ArrowDownRight size={10} className="text-red-400/60" />
                    ) : null}
                    <span className={`text-sm font-semibold ${
                      loc.multiplier > 1 ? 'text-emerald-400/70' :
                      loc.multiplier < 1 ? 'text-red-400/70' : 'text-white/40'
                    }`}>
                      {loc.multiplier > 1 ? '+' : ''}{Math.round((loc.multiplier - 1) * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
