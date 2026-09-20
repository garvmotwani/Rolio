'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, apiGet, apiPut, apiFetch, apiPost, apiDelete } from '@/lib/store';
import { formatINR } from '@/lib/format';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  MapPin, Briefcase, GraduationCap, Code, Edit3, Upload, Plus, X,
  Check, Link as LinkIcon, Github, Linkedin, User, Sparkles,
  ChevronRight, Trash2
} from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';
import TiltCard from '@/components/TiltCard';
import AnimatedCounter from '@/components/AnimatedCounter';
import CompanyLogo from '@/components/CompanyLogo';

interface Profile {
  id: number;
  user_id: number;
  title: string;
  location: string;
  bio: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
  preferred_roles: string;
  preferred_locations: string;
  preferred_work_type: string;
  target_role: string;
  salary_expectation_min: number;
  salary_expectation_max: number;
  completeness_score: number;
  skills: Array<{ id: number; name: string; level: string; category: string }>;
  experiences: Array<{
    id: number; company: string; title: string; description: string;
    location: string; start_date: string; end_date: string; is_current: boolean; achievements: string;
  }>;
  educations: Array<{
    id: number; institution: string; degree: string; field_of_study: string;
    start_date: string; end_date: string; gpa: string; description: string;
  }>;
  projects: Array<{
    id: number; name: string; description: string; technologies: string;
    url: string; github_url: string;
  }>;
}

interface ResumeData {
  id: number;
  filename: string;
  parsed_name: string;
  parsed_email: string;
  parsed_phone: string;
  parsed_skills: string[];
  parsed_education: string[];
  parsed_experience: string[];
  parsed_projects: string[];
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export default function ProfilePage() {
  const { user, hydrated } = useAuthStore();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [resume, setResume] = useState<ResumeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newSkill, setNewSkill] = useState('');
  const [editForm, setEditForm] = useState<any>({});
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) { router.push('/login'); return; }
    loadProfile();
  }, [user, hydrated, router]);

  const loadProfile = async () => {
    try {
      const p = await apiGet<Profile>('/api/profile');
      setProfile(p);
      setEditForm({
        title: p.title || '', location: p.location || '', bio: p.bio || '',
        linkedin_url: p.linkedin_url || '', github_url: p.github_url || '',
        portfolio_url: p.portfolio_url || '', preferred_roles: p.preferred_roles || '',
        preferred_locations: p.preferred_locations || '', preferred_work_type: p.preferred_work_type || 'hybrid',
        target_role: p.target_role || '',
        salary_expectation_min: p.salary_expectation_min || 0,
        salary_expectation_max: p.salary_expectation_max || 0,
      });
      try {
        const r = await apiGet<{ resume: ResumeData | null }>('/api/resume');
        setResume(r.resume);
      } catch {}
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSaveProfile = async () => {
    try {
      await apiPut('/api/profile', editForm);
      setEditing(false);
      loadProfile();
    } catch (err) { console.error(err); }
  };

  const handleUploadResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const csrfToken = document.cookie.match(/(?:^|; )rolio_csrf=([^;]*)/)?.[1] || '';
      const res = await apiFetch('/api/resume/upload', {
        method: 'POST', headers: { 'X-CSRF-Token': csrfToken }, body: formData,
      });
      if (!res.ok) { const err = await res.json(); alert(err.detail || 'Upload failed'); return; }
      const data = await res.json();
      setResume(data.resume);
      loadProfile();
    } catch (err) { console.error(err); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const handleAddSkill = async () => {
    if (!newSkill.trim()) return;
    try {
      await apiPost('/api/profile/skills', { name: newSkill.trim(), level: 'intermediate', category: 'technical' });
      setNewSkill('');
      loadProfile();
    } catch (err) { console.error(err); }
  };

  const handleDeleteSkill = async (skillId: number) => {
    try {
      await apiDelete(`/api/profile/skills/${skillId}`);
      loadProfile();
    } catch (err) { console.error(err); }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-10 space-y-4">
        <div className="skeleton h-10 w-48" />
        <div className="skeleton h-40 rounded-xl" />
        <div className="skeleton h-32 rounded-xl" />
        <div className="skeleton h-32 rounded-xl" />
      </div>
    );
  }

  if (!profile) return null;
  const score = Math.round(profile.completeness_score);

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 relative">
      <FloatingOrbs count={2} className="opacity-10" />

      <motion.div variants={container} initial="hidden" animate="show" className="relative z-10">
        {/* Header */}
        <motion.div variants={item} className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="page-title">Profile</h1>
              <p className="page-subtitle">{user?.name}</p>
            </div>
            <div className="flex items-center gap-2">
              <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleUploadResume} />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="text-xs text-white/35 hover:text-white/60 flex items-center gap-1.5 border border-white/[0.06] px-3.5 py-2 rounded-full transition-all hover:border-white/[0.12]"
              >
                <Upload size={13} /> {uploading ? 'Uploading...' : 'Resume'}
              </button>
              {!editing && (
                <button
                  onClick={() => setEditing(true)}
                  className="btn-premium text-xs bg-white text-black px-4 py-2 rounded-full font-medium flex items-center gap-1.5"
                >
                  <Edit3 size={13} /> Edit
                </button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Profile Strength */}
        <motion.div variants={item}>
          <TiltCard tiltAmount={1}>
            <div className="section-card overflow-hidden">
              <div className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                      <Sparkles size={14} className="text-white/40" />
                    </div>
                    <h2 className="text-sm font-semibold">Profile Strength</h2>
                  </div>
                  <span className="text-2xl font-bold">
                    <AnimatedCounter end={score} />%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-white rounded-full animate-progress-fill"
                    style={{ width: `${score}%` }}
                  />
                </div>
                <p className="text-[11px] text-white/20 mt-2">
                  {score >= 80 ? 'Your profile is looking great!' :
                   score >= 50 ? 'Add more details to improve matches.' :
                   'Complete your profile for better job recommendations.'}
                </p>
              </div>
            </div>
          </TiltCard>
        </motion.div>

        {/* Basic Info */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                  <User size={14} className="text-white/40" />
                </div>
                <h2 className="text-sm font-semibold">Basic Information</h2>
              </div>
            </div>
            <div className="section-card-body">
              {editing ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Title</label>
                      <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} placeholder="Software Engineer" />
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Location</label>
                      <input value={editForm.location} onChange={(e) => setEditForm({ ...editForm, location: e.target.value })} placeholder="San Francisco, CA" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Bio</label>
                    <textarea value={editForm.bio} onChange={(e) => setEditForm({ ...editForm, bio: e.target.value })} rows={3} placeholder="A brief description about yourself..." />
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">LinkedIn</label>
                      <input value={editForm.linkedin_url} onChange={(e) => setEditForm({ ...editForm, linkedin_url: e.target.value })} placeholder="linkedin.com/in/..." />
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">GitHub</label>
                      <input value={editForm.github_url} onChange={(e) => setEditForm({ ...editForm, github_url: e.target.value })} placeholder="github.com/..." />
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Portfolio</label>
                      <input value={editForm.portfolio_url} onChange={(e) => setEditForm({ ...editForm, portfolio_url: e.target.value })} placeholder="yoursite.com" />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Preferred Roles</label>
                      <input value={editForm.preferred_roles} onChange={(e) => setEditForm({ ...editForm, preferred_roles: e.target.value })} placeholder="Software Engineer, Full Stack..." />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Target Role</label>
                      <input value={editForm.target_role} onChange={(e) => setEditForm({ ...editForm, target_role: e.target.value })} placeholder="e.g. Backend Engineer" />
                      <p className="text-[10px] text-white/20 mt-1">Drives your career roadmap & skill-gap analysis</p>
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Work Type</label>
                      <select value={editForm.preferred_work_type} onChange={(e) => setEditForm({ ...editForm, preferred_work_type: e.target.value })}>
                        <option value="remote">Remote</option>
                        <option value="hybrid">Hybrid</option>
                        <option value="on-site">On-site</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Salary Min (₹ LPA)</label>
                      <input type="number" value={editForm.salary_expectation_min ? editForm.salary_expectation_min / 100000 : ''} onChange={(e) => setEditForm({ ...editForm, salary_expectation_min: Number(e.target.value) * 100000 })} />
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/25 mb-1.5 uppercase tracking-wider">Salary Max (₹ LPA)</label>
                      <input type="number" value={editForm.salary_expectation_max ? editForm.salary_expectation_max / 100000 : ''} onChange={(e) => setEditForm({ ...editForm, salary_expectation_max: Number(e.target.value) * 100000 })} />
                    </div>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button onClick={handleSaveProfile} className="btn-premium bg-white text-black px-5 py-2 rounded-full text-xs font-medium">Save Changes</button>
                    <button onClick={() => setEditing(false)} className="text-xs text-white/30 hover:text-white/60 px-4 py-2">Cancel</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {profile.title && <p className="text-sm text-white/60 font-medium">{profile.title}</p>}
                  {profile.location && (
                    <p className="text-xs text-white/35 flex items-center gap-1.5">
                      <MapPin size={13} className="text-white/20" /> {profile.location}
                    </p>
                  )}
                  {profile.bio && <p className="text-xs text-white/35 leading-relaxed mt-2">{profile.bio}</p>}
                  <div className="flex items-center gap-3 mt-3">
                    {profile.linkedin_url && (
                      <a href={profile.linkedin_url} target="_blank" rel="noopener noreferrer" className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-white/25 hover:text-white/50 hover:border-white/[0.1] transition-all">
                        <Linkedin size={14} />
                      </a>
                    )}
                    {profile.github_url && (
                      <a href={profile.github_url} target="_blank" rel="noopener noreferrer" className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-white/25 hover:text-white/50 hover:border-white/[0.1] transition-all">
                        <Github size={14} />
                      </a>
                    )}
                    {profile.portfolio_url && (
                      <a href={profile.portfolio_url} target="_blank" rel="noopener noreferrer" className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-white/25 hover:text-white/50 hover:border-white/[0.1] transition-all">
                        <LinkIcon size={14} />
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-xs text-white/20">
                    <span className="capitalize">{profile.preferred_work_type}</span>
                    {profile.salary_expectation_min > 0 && (
                      <span>{formatINR(profile.salary_expectation_min)} – {formatINR(profile.salary_expectation_max)} /yr</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Skills */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                  <Code size={14} className="text-white/40" />
                </div>
                <h2 className="text-sm font-semibold">Skills</h2>
                <span className="text-[10px] text-white/15 font-mono">{profile.skills.length}</span>
              </div>
            </div>
            <div className="section-card-body">
              <div className="flex flex-wrap gap-2 mb-4">
                {profile.skills.map((skill) => (
                  <span
                    key={skill.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-white/55 hover:border-white/[0.1] transition-all group"
                  >
                    {skill.name}
                    <span className="text-[9px] text-white/15 uppercase">{skill.level?.slice(0, 3)}</span>
                    <button
                      onClick={() => handleDeleteSkill(skill.id)}
                      className="text-white/0 group-hover:text-red-400/60 transition-colors ml-0.5"
                    >
                      <X size={10} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
                  placeholder="Add a skill..."
                  className="flex-1 text-xs"
                />
                <button
                  onClick={handleAddSkill}
                  className="px-4 py-2 bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.06] rounded-lg text-xs transition-all"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Experience */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                <Briefcase size={14} className="text-white/40" />
              </div>
              <h2 className="text-sm font-semibold">Experience</h2>
              <span className="text-[10px] text-white/15 font-mono">{profile.experiences.length}</span>
            </div>
            <div className="section-card-body">
              {profile.experiences.length > 0 ? (
                <div className="space-y-4">
                  {profile.experiences.map((exp, i) => (
                    <div key={exp.id} className={`flex items-start gap-4 ${i < profile.experiences.length - 1 ? 'pb-4 border-b border-white/[0.03]' : ''}`}>
                      <div className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.04] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Briefcase size={12} className="text-white/20" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{exp.title}</p>
                        <p className="text-xs text-white/35 mt-0.5">{exp.company}</p>
                        <p className="text-[11px] text-white/20 mt-1">
                          {exp.start_date} – {exp.is_current ? 'Present' : exp.end_date}
                        </p>
                        {exp.description && <p className="text-xs text-white/30 mt-2 leading-relaxed">{exp.description}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-white/20 py-4 text-center">No experience added yet</p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Education */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                <GraduationCap size={14} className="text-white/40" />
              </div>
              <h2 className="text-sm font-semibold">Education</h2>
              <span className="text-[10px] text-white/15 font-mono">{profile.educations.length}</span>
            </div>
            <div className="section-card-body">
              {profile.educations.length > 0 ? (
                <div className="space-y-4">
                  {profile.educations.map((edu, i) => (
                    <div key={edu.id} className={`flex items-start gap-4 ${i < profile.educations.length - 1 ? 'pb-4 border-b border-white/[0.03]' : ''}`}>
                      <div className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.04] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <GraduationCap size={12} className="text-white/20" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{edu.degree} {edu.field_of_study && <span className="text-white/40">in {edu.field_of_study}</span>}</p>
                        <p className="text-xs text-white/35 mt-0.5">{edu.institution}</p>
                        <p className="text-[11px] text-white/20 mt-1">{edu.start_date} – {edu.end_date}</p>
                        {edu.gpa && <p className="text-[11px] text-white/20 mt-1">GPA: {edu.gpa}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-white/20 py-4 text-center">No education added yet</p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Projects */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                <Code size={14} className="text-white/40" />
              </div>
              <h2 className="text-sm font-semibold">Projects</h2>
              <span className="text-[10px] text-white/15 font-mono">{profile.projects.length}</span>
            </div>
            <div className="section-card-body">
              {profile.projects.length > 0 ? (
                <div className="space-y-4">
                  {profile.projects.map((proj, i) => (
                    <div key={proj.id} className={`flex items-start gap-4 ${i < profile.projects.length - 1 ? 'pb-4 border-b border-white/[0.03]' : ''}`}>
                      <div className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.04] flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Code size={12} className="text-white/20" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{proj.name}</p>
                        {proj.description && <p className="text-xs text-white/30 mt-1 leading-relaxed">{proj.description}</p>}
                        {proj.technologies && <p className="text-[11px] text-white/20 mt-1">Tech: {proj.technologies}</p>}
                        <div className="flex gap-3 mt-2">
                          {proj.url && <a href={proj.url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-white/30 hover:text-white/60 transition-colors">Live →</a>}
                          {proj.github_url && <a href={proj.github_url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-white/30 hover:text-white/60 transition-colors">Code →</a>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-white/20 py-4 text-center">No projects added yet</p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Resume */}
        <motion.div variants={item} className="mt-4">
          <div className="section-card">
            <div className="section-card-header flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center">
                <Upload size={14} className="text-white/40" />
              </div>
              <h2 className="text-sm font-semibold">Resume</h2>
            </div>
            <div className="section-card-body">
              {resume ? (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                    <span className="text-lg">📄</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white/60">{resume.filename}</p>
                    {resume.parsed_skills?.length > 0 && (
                      <p className="text-xs text-white/25 mt-0.5">{resume.parsed_skills.length} skills extracted</p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Upload size={24} className="text-white/10 mx-auto mb-3" />
                  <p className="text-xs text-white/30 mb-3">No resume uploaded</p>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="text-xs text-white/40 hover:text-white/60 border border-white/[0.06] px-4 py-2 rounded-full transition-all hover:border-white/[0.12]"
                  >
                    Upload resume
                  </button>
                </div>
              )}
              {/* AI Resume Builder link */}
              <div className="mt-4 pt-4 border-t border-white/[0.04]">
                <Link
                  href="/resume-builder"
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all group"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center group-hover:bg-white/[0.08] transition-colors">
                    <Sparkles size={16} className="text-white/30 group-hover:text-white/60 transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white/60 group-hover:text-white/80 transition-colors">AI Resume Builder</p>
                    <p className="text-xs text-white/20">Generate a tailored, ATS-friendly resume</p>
                  </div>
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}


