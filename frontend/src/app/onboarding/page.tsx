'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore, apiPost, apiFetch } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, ArrowLeft, Check, Loader2, Upload, Sparkles, GraduationCap, Briefcase, Code, Target, MapPin, Laptop, DollarSign, FileText, Rocket } from 'lucide-react';
import FloatingOrbs from '@/components/FloatingOrbs';

const steps = [
  { id: 1, title: 'Your name', subtitle: 'Tell us what to call you', icon: Sparkles },
  { id: 2, title: 'Education', subtitle: 'Where did you study?', icon: GraduationCap },
  { id: 3, title: 'Experience', subtitle: 'Your work history', icon: Briefcase },
  { id: 4, title: 'Skills', subtitle: 'What are you good at?', icon: Code },
  { id: 5, title: 'Desired roles', subtitle: 'What positions interest you?', icon: Target },
  { id: 6, title: 'Preferred locations', subtitle: 'Where do you want to work?', icon: MapPin },
  { id: 7, title: 'Work type', subtitle: 'Remote, hybrid, or on-site?', icon: Laptop },
  { id: 8, title: 'Salary expectations', subtitle: 'What are you targeting?', icon: DollarSign },
  { id: 9, title: 'Resume', subtitle: 'Upload your resume (optional)', icon: FileText },
  { id: 10, title: 'Career goals', subtitle: 'A brief summary of what you want', icon: Rocket },
];

export default function OnboardingPage() {
  const { user, setAuth } = useAuthStore();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);

  const [data, setData] = useState({
    name: user?.name || '',
    education: [{ institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', gpa: '' }],
    experience: [{ company: '', title: '', description: '', start_date: '', end_date: '', is_current: false }],
    skills: [''],
    preferred_roles: '',
    preferred_locations: '',
    preferred_work_type: 'hybrid',
    salary_min: 0,
    salary_max: 0,
    bio: '',
  });

  const [resumeFile, setResumeFile] = useState<File | null>(null);

  const updateData = (field: string, value: any) => setData((d) => ({ ...d, [field]: value }));

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      if (resumeFile) {
        const formData = new FormData();
        formData.append('file', resumeFile);
        const csrfToken = document.cookie.match(/(?:^|; )rolio_csrf=([^;]*)/)?.[1] || '';
        await apiFetch('/api/resume/upload', {
          method: 'POST',
          headers: { 'X-CSRF-Token': csrfToken },
          body: formData,
        });
      }

      const result = await apiPost('/api/onboarding', {
        name: data.name,
        title: data.preferred_roles.split(',')[0]?.trim() || '',
        education: data.education.filter((e) => e.institution),
        experience: data.experience.filter((e) => e.company),
        skills: data.skills.filter((s) => s.trim()).map((s) => ({ name: s.trim(), level: 'intermediate', category: 'technical' })),
        preferred_roles: data.preferred_roles,
        preferred_locations: data.preferred_locations,
        preferred_work_type: data.preferred_work_type,
        salary_expectation_min: data.salary_min,
        salary_expectation_max: data.salary_max,
        bio: data.bio,
      });

      if (user) {
        setAuth({ ...user, name: data.name, is_onboarded: true });
      }

      router.push('/dashboard');
    } catch (err) {
      console.error(err);
      alert('Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const progress = (step / steps.length) * 100;
  const CurrentIcon = steps[step - 1].icon;

  const slideVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 60 : -60,
      opacity: 0,
      filter: 'blur(4px)',
      scale: 0.98,
    }),
    center: { x: 0, opacity: 1, filter: 'blur(0px)', scale: 1 },
    exit: (direction: number) => ({
      x: direction < 0 ? 60 : -60,
      opacity: 0,
      filter: 'blur(4px)',
      scale: 0.98,
    }),
  };

  // Calculate SVG circle progress
  const circleRadius = 18;
  const circleCircumference = 2 * Math.PI * circleRadius;
  const circleOffset = circleCircumference * (1 - step / steps.length);

  return (
    <div className="min-h-screen flex flex-col relative">
      <FloatingOrbs count={2} className="opacity-20" />

      {/* Progress bar */}
      <div className="fixed top-0 left-0 right-0 h-[2px] bg-white/[0.03] z-50">
        <motion.div
          className="h-full bg-white/70"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{ boxShadow: '0 0 12px rgba(255,255,255,0.3)' }}
        />
      </div>

      <div className="flex-1 flex items-center justify-center px-6 py-16 relative z-10">
        <div className="w-full max-w-lg">
          {/* Step indicator with SVG ring */}
          <div className="flex items-center gap-4 mb-8">
            <div className="relative flex-shrink-0">
              <svg width="44" height="44" viewBox="0 0 44 44" className="transform -rotate-90">
                <circle cx="22" cy="22" r={circleRadius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="2" />
                <motion.circle
                  cx="22" cy="22" r={circleRadius}
                  fill="none"
                  stroke="rgba(255,255,255,0.4)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeDasharray={circleCircumference}
                  initial={{ strokeDashoffset: circleCircumference }}
                  animate={{ strokeDashoffset: circleOffset }}
                  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <CurrentIcon size={14} className="text-white/50" />
              </div>
            </div>
            <div>
              <p className="text-xs text-white/25">
                <span className="text-white/50 font-medium">{step}</span>
                <span className="text-white/15"> / {steps.length}</span>
                <span className="text-white/15"> — {steps[step - 1].subtitle}</span>
              </p>
              <div className="flex gap-0.5 mt-2">
                {steps.map((_, i) => (
                  <motion.div
                    key={i}
                    className="rounded-full"
                    initial={false}
                    animate={{
                      width: i < step ? 16 : i === step ? 16 : 6,
                      backgroundColor: i < step ? 'rgba(255,255,255,0.4)' : i === step ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.05)',
                    }}
                    transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                    style={{ height: 3 }}
                  />
                ))}
              </div>
            </div>
          </div>

          <AnimatePresence mode="wait" custom={1}>
            <motion.div
              key={step}
              custom={1}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <h2 className="text-2xl font-bold tracking-tight mb-1">{steps[step - 1].title}</h2>
              <p className="text-sm text-white/25 mb-8">{steps[step - 1].subtitle}</p>

              {/* Step content */}
              {step === 1 && (
                <input
                  value={data.name}
                  onChange={(e) => updateData('name', e.target.value)}
                  placeholder="Your full name"
                  autoFocus
                />
              )}

              {step === 2 && (
                <div className="space-y-3">
                  {data.education.map((edu, i) => (
                    <div key={i} className="p-4 bg-[#050505] border border-white/[0.04] rounded-lg space-y-2">
                      <input
                        value={edu.institution}
                        onChange={(e) => { const newEdu = [...data.education]; newEdu[i].institution = e.target.value; updateData('education', newEdu); }}
                        placeholder="Institution name"
                      />
                      <div className="grid grid-cols-2 gap-2">
                        <input value={edu.degree} onChange={(e) => { const newEdu = [...data.education]; newEdu[i].degree = e.target.value; updateData('education', newEdu); }} placeholder="Degree (e.g. B.S.)" />
                        <input value={edu.field_of_study} onChange={(e) => { const newEdu = [...data.education]; newEdu[i].field_of_study = e.target.value; updateData('education', newEdu); }} placeholder="Field of study" />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <input value={edu.start_date} onChange={(e) => { const newEdu = [...data.education]; newEdu[i].start_date = e.target.value; updateData('education', newEdu); }} placeholder="Start (e.g. 2020)" />
                        <input value={edu.end_date} onChange={(e) => { const newEdu = [...data.education]; newEdu[i].end_date = e.target.value; updateData('education', newEdu); }} placeholder="End (e.g. 2024)" />
                      </div>
                    </div>
                  ))}
                  <button onClick={() => updateData('education', [...data.education, { institution: '', degree: '', field_of_study: '', start_date: '', end_date: '', gpa: '' }])} className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors">
                    + Add another
                  </button>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-3">
                  {data.experience.map((exp, i) => (
                    <div key={i} className="p-4 bg-[#050505] border border-white/[0.04] rounded-lg space-y-2">
                      <input value={exp.company} onChange={(e) => { const newExp = [...data.experience]; newExp[i].company = e.target.value; updateData('experience', newExp); }} placeholder="Company name" />
                      <input value={exp.title} onChange={(e) => { const newExp = [...data.experience]; newExp[i].title = e.target.value; updateData('experience', newExp); }} placeholder="Job title" />
                      <div className="grid grid-cols-2 gap-2">
                        <input value={exp.start_date} onChange={(e) => { const newExp = [...data.experience]; newExp[i].start_date = e.target.value; updateData('experience', newExp); }} placeholder="Start (e.g. 2021)" />
                        <input value={exp.end_date} onChange={(e) => { const newExp = [...data.experience]; newExp[i].end_date = e.target.value; updateData('experience', newExp); }} placeholder="End (or present)" />
                      </div>
                    </div>
                  ))}
                  <button onClick={() => updateData('experience', [...data.experience, { company: '', title: '', description: '', start_date: '', end_date: '', is_current: false }])} className="text-xs text-white/25 hover:text-white/50 flex items-center gap-1 transition-colors">
                    + Add another
                  </button>
                </div>
              )}

              {step === 4 && (
                <div className="space-y-3">
                  <p className="text-xs text-white/15">Enter skills one per line or separated by commas</p>
                  <textarea
                    value={data.skills.join('\n')}
                    onChange={(e) => updateData('skills', e.target.value.split('\n').flatMap((l) => l.split(',').map((s) => s.trim())).filter(Boolean))}
                    rows={6}
                    placeholder="Python&#10;JavaScript&#10;React&#10;SQL&#10;FastAPI"
                  />
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {data.skills.filter(Boolean).map((s, i) => (
                      <span key={i} className="px-2.5 py-1 bg-white/[0.04] border border-white/[0.06] rounded-full text-xs text-white/50">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {step === 5 && (
                <input value={data.preferred_roles} onChange={(e) => updateData('preferred_roles', e.target.value)} placeholder="Software Engineer, Full Stack Developer, etc." />
              )}

              {step === 6 && (
                <input value={data.preferred_locations} onChange={(e) => updateData('preferred_locations', e.target.value)} placeholder="San Francisco, Remote, New York, etc." />
              )}

              {step === 7 && (
                <div className="grid grid-cols-3 gap-3">
                  {['remote', 'hybrid', 'on-site'].map((wt) => (
                    <motion.button
                      key={wt}
                      onClick={() => updateData('preferred_work_type', wt)}
                      whileTap={{ scale: 0.97 }}
                      className={`p-5 rounded-xl border text-sm capitalize transition-all duration-300 relative overflow-hidden ${
                        data.preferred_work_type === wt
                          ? 'border-white/30 bg-white/[0.08] text-white shadow-[0_0_24px_rgba(255,255,255,0.04)]'
                          : 'border-white/[0.06] text-white/35 hover:text-white/50 hover:border-white/[0.12] hover:bg-white/[0.02]'
                      }`}
                    >
                      {data.preferred_work_type === wt && (
                        <motion.div
                          layoutId="worktype-bg"
                          className="absolute inset-0 bg-white/[0.04]"
                          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                        />
                      )}
                      <span className="relative z-10">
                        {wt === 'on-site' ? '🏢 On-site' : wt === 'remote' ? '🌍 Remote' : '🔄 Hybrid'}
                      </span>
                    </motion.button>
                  ))}
                </div>
              )}

              {step === 8 && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-white/25 mb-1.5">Minimum (₹ LPA)</label>
                      <input type="number" value={data.salary_min ? data.salary_min / 100000 : ''} onChange={(e) => updateData('salary_min', Number(e.target.value) * 100000)} placeholder="12" />
                    </div>
                    <div>
                      <label className="block text-xs text-white/25 mb-1.5">Maximum (₹ LPA)</label>
                      <input type="number" value={data.salary_max ? data.salary_max / 100000 : ''} onChange={(e) => updateData('salary_max', Number(e.target.value) * 100000)} placeholder="35" />
                    </div>
                  </div>
                  <p className="text-[11px] text-white/20">Enter annual figures in lakhs — e.g. 12 LPA = ₹12,00,000/year</p>
                </div>
              )}

              {step === 9 && (
                <div className="space-y-4">
                  <div className={`p-10 border-2 border-dashed rounded-2xl text-center transition-all duration-500 relative ${
                    resumeFile
                      ? 'border-white/20 bg-white/[0.04]'
                      : 'border-white/[0.08] hover:border-white/[0.15] bg-white/[0.01] hover:bg-white/[0.02]'
                  }`}>
                    <Upload size={28} className={`mx-auto mb-4 transition-colors duration-300 ${resumeFile ? 'text-white/40' : 'text-white/15'}`} />
                    {resumeFile ? (
                      <div>
                        <p className="text-sm text-white/60 font-medium">{resumeFile.name}</p>
                        <p className="text-xs text-white/25 mt-1">{(resumeFile.size / 1024).toFixed(0)} KB</p>
                        <button onClick={() => setResumeFile(null)} className="text-xs text-white/30 mt-3 hover:text-white/60 transition-colors underline underline-offset-2">
                          Remove
                        </button>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm text-white/40">Drop your resume or click to browse</p>
                        <p className="text-xs text-white/15 mt-1.5">PDF or DOCX, max 5MB</p>
                        <input type="file" accept=".pdf,.docx" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-white/15 text-center">You can skip this step and upload later from your profile.</p>
                </div>
              )}

              {step === 10 && (
                <div className="space-y-3">
                  <textarea
                    value={data.bio}
                    onChange={(e) => updateData('bio', e.target.value)}
                    rows={4}
                    placeholder="I'm a software engineer passionate about building scalable systems and great user experiences..."
                  />
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-10">
            <button
              onClick={() => setStep(Math.max(1, step - 1))}
              disabled={step === 1}
              className="flex items-center gap-2 text-sm text-white/25 hover:text-white/50 disabled:opacity-20 disabled:cursor-not-allowed transition-all duration-300 px-4 py-2 rounded-full hover:bg-white/[0.03]"
            >
              <ArrowLeft size={14} /> Back
            </button>

            {step < steps.length ? (
              <button
                onClick={() => setStep(step + 1)}
                className="bg-white text-black px-7 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 hover:bg-white/90 transition-all duration-300 shadow-[0_0_24px_rgba(255,255,255,0.04)] hover:shadow-[0_0_32px_rgba(255,255,255,0.08)] hover:-translate-y-0.5 active:translate-y-0"
              >
                Continue <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="bg-white text-black px-7 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 hover:bg-white/90 transition-all duration-300 disabled:opacity-50 shadow-[0_0_24px_rgba(255,255,255,0.04)] hover:shadow-[0_0_32px_rgba(255,255,255,0.08)] hover:-translate-y-0.5 active:translate-y-0"
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                {submitting ? 'Creating profile...' : 'Complete Setup'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
