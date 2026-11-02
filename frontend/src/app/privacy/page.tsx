import Link from 'next/link';

export const metadata = {
  title: 'Privacy Policy | Rolio',
  description: 'Privacy information for the Rolio portfolio demo.',
};

export default function PrivacyPage() {
  return (
    <section className="max-w-3xl mx-auto px-6 py-20 text-white">
      <p className="text-xs tracking-[0.25em] text-white/30 uppercase mb-4">Portfolio demo</p>
      <h1 className="text-4xl font-bold tracking-tight mb-8">Privacy Policy</h1>
      <div className="space-y-6 text-sm leading-7 text-white/60">
        <p>Rolio is a portfolio project. It stores the information you provide to operate its job-matching and application-tracking features.</p>
        <p>Account details, profile information, applications, and uploaded resume content are used only to provide the app experience. Optional Google and Gmail integrations are only used after you explicitly connect them.</p>
        <p>Do not upload sensitive information you would not want stored in a demo application. You can delete your account data through the application or contact the project owner through the repository.</p>
        <p>This page is a plain-language portfolio notice, not legal advice or a commercial privacy policy.</p>
      </div>
      <Link href="/" className="inline-block mt-10 text-sm text-white/50 hover:text-white transition-colors">← Back to Rolio</Link>
    </section>
  );
}
