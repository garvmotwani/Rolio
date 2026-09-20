'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuthStore, apiGet, apiPost, apiDelete } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, X, Briefcase, Sparkles, TrendingUp, MapPin, Bookmark, History } from 'lucide-react';
import JobCard from '@/components/JobCard';
import FloatingOrbs from '@/components/FloatingOrbs';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface Job {
  id: number | string;
  title: string;
  company_name: string;
  company_logo: string;
  location: string;
  work_type: string;
  salary_min: number;
  salary_max: number;
  skills_required?: string;
  skills?: string[];
  match_score: number;
  posted_at: string;
  is_saved: boolean;
  is_applied: boolean;
  experience_level: string;
  source?: string;
}

interface SearchResults {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

interface SearchEntry {
  id: number;
  query: string;
  location: string;
  work_type: string;
  experience_level: string;
  source: string;
  results_count: number;
  created_at: string;
}

const workTypes = ['remote', 'hybrid', 'on-site'];
const experienceLevels = ['intern', 'junior', 'mid', 'senior', 'lead'];
const sortOptions = [
  { value: 'best_match', label: 'Best Match', icon: '🎯' },
  { value: 'most_recent', label: 'Most Recent', icon: '🕐' },
  { value: 'salary', label: 'Highest Salary', icon: '💰' },
];

export default function JobsContent() {
  const searchParams = useSearchParams();
  const { user } = useAuthStore();

  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [location, setLocation] = useState(searchParams.get('location') || '');
  const [workType, setWorkType] = useState(searchParams.get('work_type') || '');
  const [experienceLevel, setExperienceLevel] = useState(searchParams.get('experience_level') || '');
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'best_match');
  const [page, setPage] = useState(1);

  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const popularSearches = ['React', 'Python', 'TypeScript', 'Remote', 'Senior', 'Frontend', 'Backend', 'Full Stack', 'DevOps', 'Data Science', 'Machine Learning', 'UI/UX'];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    if (query.length > 0) {
      const filtered = popularSearches.filter(s => s.toLowerCase().includes(query.toLowerCase()));
      setSuggestions(filtered.slice(0, 5));
    } else {
      setSuggestions(popularSearches.slice(0, 6));
    }
  }, [query]);

  const [searchSource, setSearchSource] = useState<'all' | 'local' | 'jsearch'>('all');
  const [searchHistory, setSearchHistory] = useState<SearchEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (location) params.set('location', location);
      if (workType) params.set('work_type', workType);
      if (experienceLevel) params.set('experience_level', experienceLevel);
      params.set('source', searchSource);
      params.set('page', page.toString());
      params.set('per_page', '20');

      const data = await apiGet<any>(`/api/search?${params.toString()}`);
      setResults({
        jobs: data.jobs || [],
        total: data.total || 0,
        page: data.page || 1,
        per_page: data.per_page || 20,
      });
    } catch (err) {
      // Fallback to local-only search
      try {
        const params = new URLSearchParams();
        if (query) params.set('query', query);
        if (location) params.set('location', location);
        if (workType) params.set('work_type', workType);
        if (experienceLevel) params.set('experience_level', experienceLevel);
        params.set('sort_by', sortBy);
        params.set('page', page.toString());
        params.set('per_page', '12');
        const data = await apiGet<SearchResults>(`/api/jobs?${params.toString()}`);
        setResults(data);
      } catch (err2) {
        console.error(err2);
      }
    } finally {
      setLoading(false);
    }
  }, [query, location, workType, experienceLevel, sortBy, page, searchSource]);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  // Load search history for logged-in users
  useEffect(() => {
    if (!user) return;
    apiGet<SearchEntry[]>('/api/search/history?limit=8').then(setSearchHistory).catch(() => {});
  }, [user]);

  const saveCurrentSearch = async () => {
    if (!user) return;
    try {
      const params = new URLSearchParams();
      if (query) params.set('query', query);
      if (location) params.set('location', location);
      if (workType) params.set('work_type', workType);
      if (experienceLevel) params.set('experience_level', experienceLevel);
      params.set('source', searchSource);
      params.set('results_count', String(results?.total || 0));
      await apiPost(`/api/search/history?${params.toString()}`, {});
      const updated = await apiGet<SearchEntry[]>('/api/search/history?limit=8');
      setSearchHistory(updated);
    } catch (err) { console.error(err); }
  };

  const deleteSearch = async (id: number) => {
    try {
      await apiDelete(`/api/search/history/${id}`);
      setSearchHistory(prev => prev.filter(s => s.id !== id));
    } catch (err) { console.error(err); }
  };

  const applySearch = (entry: SearchEntry) => {
    setQuery(entry.query || '');
    setLocation(entry.location || '');
    setWorkType(entry.work_type || '');
    setExperienceLevel(entry.experience_level || '');
    setSearchSource((entry.source as any) || 'all');
    setPage(1);
    setShowHistory(false);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadJobs();
  };

  const clearFilters = () => {
    setQuery('');
    setLocation('');
    setWorkType('');
    setExperienceLevel('');
    setSortBy('best_match');
    setPage(1);
  };

  const canSave = user && (query || location);

  const hasFilters = workType || experienceLevel || location;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-15" />

      <div className="relative z-10">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Find Jobs</h1>
          <p className="text-white/30 text-sm mt-1">
            Search across {results?.total || 0} opportunities
          </p>
        </motion.div>

        {/* Search bar */}
        <motion.form
          onSubmit={handleSearch}
          className="mb-6"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <div className="flex gap-2">
            <div className="flex-1 relative" ref={searchRef}>
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/15" />
              <input
                type="text"
                value={query}
                onChange={(e) => { setQuery(e.target.value); setShowSuggestions(true); }}
                onFocus={() => setShowSuggestions(true)}
                placeholder="Try “internships in Bangalore using Python” or job title, skill..."
                className="pl-9 pr-4"
              />
              {showSuggestions && suggestions.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-full left-0 right-0 mt-1 bg-[#0a0a0a] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50"
                >
                  <div className="px-3 py-2 text-[10px] text-white/25 uppercase tracking-wider">
                    {query.length > 0 ? 'Suggestions' : 'Popular searches'}
                  </div>
                  {suggestions.map((s, i) => (
                    <button
                      key={s}
                      onClick={() => { setQuery(s); setShowSuggestions(false); handleSearch(new Event('submit') as any); }}
                      className="w-full px-3 py-2 text-left text-sm text-white/60 hover:bg-white/[0.05] hover:text-white/80 flex items-center gap-2 transition-colors"
                    >
                      <Search size={12} className="text-white/20" />
                      {s}
                    </button>
                  ))}
                </motion.div>
              )}
            </div>
            <div className="w-52 relative">
              <MapPin size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/15" />
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location"
                className="pl-9 pr-4"
              />
            </div>
            <button
              type="submit"
              className="bg-white text-black px-6 py-2.5 rounded-lg font-medium text-sm hover:bg-white/90 transition-all flex-shrink-0"
            >
              Search
            </button>
            {canSave && (
              <button
                type="button"
                onClick={saveCurrentSearch}
                title="Save this search for later"
                className="px-3 py-2.5 rounded-lg border border-white/[0.06] text-sm text-white/35 hover:text-white/55 hover:border-white/[0.12] transition-all duration-300 flex-shrink-0"
              >
                <Bookmark size={14} />
              </button>
            )}
            {user && searchHistory.length > 0 && (
              <button
                type="button"
                onClick={() => setShowHistory(!showHistory)}
                className={`px-3 py-2.5 rounded-lg border text-sm flex items-center gap-1.5 transition-all duration-300 flex-shrink-0 ${
                  showHistory ? 'border-white/15 text-white/70 bg-white/[0.04]' : 'border-white/[0.06] text-white/35 hover:text-white/55 hover:border-white/[0.1]'
                }`}
                title="Recent searches"
              >
                <History size={14} />
              </button>
            )}
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 py-2.5 rounded-lg border text-sm flex items-center gap-1.5 transition-all duration-300 ${
                showFilters || hasFilters
                  ? 'border-white/15 text-white/70 bg-white/[0.04]'
                  : 'border-white/[0.06] text-white/35 hover:text-white/55 hover:border-white/[0.1]'
              }`}
            >
              <Filter size={14} />
              <span className="hidden sm:inline">Filters</span>
            </button>
          </div>
        </motion.form>

        {/* Recent searches dropdown */}
        <AnimatePresence>
          {showHistory && searchHistory.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="mb-6 p-4 bg-[#050505] border border-white/[0.05] rounded-xl"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] uppercase tracking-wider text-white/25 flex items-center gap-1.5">
                  <History size={10} /> Recent Searches
                </span>
                <button
                  onClick={async () => {
                    try {
                      await apiDelete('/api/search/history');
                      setSearchHistory([]);
                    } catch (err) { console.error(err); }
                  }}
                  className="text-[10px] text-white/20 hover:text-white/40 transition-colors"
                >
                  Clear all
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {searchHistory.map((entry) => (
                  <div
                    key={entry.id}
                    className="group flex items-center gap-1.5 bg-white/[0.03] border border-white/[0.06] hover:border-white/[0.12] rounded-lg transition-all"
                  >
                    <button
                      onClick={() => applySearch(entry)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white/50 hover:text-white/75 transition-colors"
                    >
                      <Search size={10} className="text-white/20" />
                      {entry.query || 'All jobs'}
                      {entry.location && (
                        <span className="text-white/25">· {entry.location}</span>
                      )}
                      {entry.experience_level && (
                        <span className="text-[9px] text-white/20 uppercase">{entry.experience_level}</span>
                      )}
                      {entry.results_count > 0 && (
                        <span className="text-[9px] font-mono text-white/20">{entry.results_count}</span>
                      )}
                    </button>
                    <button
                      onClick={() => deleteSearch(entry.id)}
                      className="pr-2 text-white/15 hover:text-white/50 transition-colors"
                      title="Remove"
                    >
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0, marginBottom: 0 }}
              animate={{ opacity: 1, height: 'auto', marginBottom: 24 }}
              exit={{ opacity: 0, height: 0, marginBottom: 0 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <div className="p-5 bg-[#050505] border border-white/[0.04] rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs text-white/25 uppercase tracking-wider">Filters</span>
                  {hasFilters && (
                    <button onClick={clearFilters} className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors">
                      <X size={12} /> Clear all
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-[10px] text-white/25 mb-2 uppercase tracking-wider">Location</label>
                    <div className="relative">
                      <MapPin size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" />
                      <input
                        type="text"
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                        placeholder="City, state, or country"
                        className="pl-8 pr-3 py-1.5 text-xs"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/25 mb-2 uppercase tracking-wider">Work Type</label>
                    <div className="flex flex-wrap gap-1.5">
                      {workTypes.map((wt) => (
                        <button
                          key={wt}
                          onClick={() => setWorkType(workType === wt ? '' : wt)}
                          className={`px-3 py-1.5 rounded-full text-xs capitalize transition-all duration-300 ${
                            workType === wt
                              ? 'bg-white text-black font-medium'
                              : 'bg-white/[0.04] text-white/45 hover:text-white/65 hover:bg-white/[0.06]'
                          }`}
                        >
                          {wt}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/25 mb-2 uppercase tracking-wider">Experience</label>
                    <div className="flex flex-wrap gap-1.5">
                      {experienceLevels.map((el) => (
                        <button
                          key={el}
                          onClick={() => setExperienceLevel(experienceLevel === el ? '' : el)}
                          className={`px-3 py-1.5 rounded-full text-xs capitalize transition-all duration-300 ${
                            experienceLevel === el
                              ? 'bg-white text-black font-medium'
                              : 'bg-white/[0.04] text-white/45 hover:text-white/65 hover:bg-white/[0.06]'
                          }`}
                        >
                          {el}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-[10px] text-white/25 mb-2 uppercase tracking-wider">Sort By</label>
                    <div className="flex flex-wrap gap-1.5">
                      {sortOptions.map((opt) => (
                        <button
                          key={opt.value}
                          onClick={() => setSortBy(opt.value)}
                          className={`px-3 py-1.5 rounded-full text-xs transition-all duration-300 flex items-center gap-1 ${
                            sortBy === opt.value
                              ? 'bg-white text-black font-medium'
                              : 'bg-white/[0.04] text-white/45 hover:text-white/65 hover:bg-white/[0.06]'
                          }`}
                        >
                          <span className="text-[10px]">{opt.icon}</span>
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {/* Source toggle */}
                <div className="mt-4 pt-4 border-t border-white/[0.04]">
                  <label className="block text-[10px] text-white/25 mb-2 uppercase tracking-wider">Job Source</label>
                  <div className="flex gap-1.5">
                    {([
                      { value: 'all' as const, label: 'All Jobs', icon: '🌐' },
                      { value: 'local' as const, label: 'Database', icon: '💾' },
                      { value: 'jsearch' as const, label: 'Google for Jobs', icon: '🔍' },
                    ]).map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => { setSearchSource(opt.value); setPage(1); }}
                        className={`px-3 py-1.5 rounded-full text-xs transition-all duration-300 flex items-center gap-1 ${
                          searchSource === opt.value
                            ? 'bg-white text-black font-medium'
                            : 'bg-white/[0.04] text-white/45 hover:text-white/65 hover:bg-white/[0.06]'
                        }`}
                      >
                        <span className="text-[10px]">{opt.icon}</span>
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Active filter chips */}
        <AnimatePresence>
          {hasFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap gap-2 mb-4 overflow-hidden"
            >
              {workType && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full text-xs text-white/50"
                >
                  <span className="capitalize">{workType}</span>
                  <button onClick={() => setWorkType('')} className="hover:text-white/80 transition-colors"><X size={10} /></button>
                </motion.span>
              )}
              {experienceLevel && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full text-xs text-white/50 capitalize"
                >
                  {experienceLevel}
                  <button onClick={() => setExperienceLevel('')} className="hover:text-white/80 transition-colors"><X size={10} /></button>
                </motion.span>
              )}
              {location && (
                <motion.span
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] rounded-full text-xs text-white/50"
                >
                  {location}
                  <button onClick={() => setLocation('')} className="hover:text-white/80 transition-colors"><X size={10} /></button>
                </motion.span>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className="skeleton h-40 rounded-xl"
              />
            ))}
          </div>
        ) : results && results.jobs.length > 0 ? (
          <>
            <div className="space-y-3">
              <AnimatePresence mode="wait">
                {results.jobs.map((job, i) => (
                  <motion.div
                    key={job.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04, duration: 0.4 }}
                  >
                    <JobCard job={job} onSaveChange={loadJobs} />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Pagination */}
            {results.total > results.per_page && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center gap-3 mt-10"
              >
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="px-4 py-2 text-sm text-white/35 hover:text-white/60 disabled:opacity-25 disabled:cursor-not-allowed border border-white/[0.06] rounded-lg transition-all hover:border-white/[0.12]"
                >
                  Previous
                </button>
                <span className="text-sm text-white/25 font-mono">
                  {page} / {Math.ceil(results.total / results.per_page)}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= Math.ceil(results.total / results.per_page)}
                  className="px-4 py-2 text-sm text-white/35 hover:text-white/60 disabled:opacity-25 disabled:cursor-not-allowed border border-white/[0.06] rounded-lg transition-all hover:border-white/[0.12]"
                >
                  Next
                </button>
              </motion.div>
            )}
          </>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-24"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mx-auto mb-5">
              <Briefcase size={28} className="text-white/10" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No jobs found</h3>
            <p className="text-white/25 text-sm max-w-sm mx-auto leading-relaxed mb-6">
              Try adjusting your search terms or filters to discover more opportunities.
            </p>
            {hasFilters ? (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-2 bg-white text-black px-6 py-2.5 rounded-full text-sm font-medium hover:bg-white/90 transition-all"
              >
                Clear all filters
              </button>
            ) : (
              <p className="text-xs text-white/15">Try different keywords or check back later</p>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
