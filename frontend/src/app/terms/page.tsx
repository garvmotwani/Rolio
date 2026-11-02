import Link from 'next/link';

export const metadata = {
  title: 'Terms of Use | Rolio',
  description: 'Terms of use for the Rolio portfolio demo.',
};

export default function TermsPage() {
  return (
    <section className="max-w-3xl mx-auto px-6 py-20 text-white">
      <p className="text-xs tracking-[0.25em] text-white/30 uppercase mb-4">Portfolio demo</p>
      <h1 className="text-4xl font-bold tracking-tight mb-8">Terms of Use</h1>
      <div className="space-y-6 text-sm leading-7 text-white/60">
        <p>Rolio is provided as a portfolio demonstration. It is not a recruitment service, employment agency, or guarantee of job-search results.</p>
        <p>Use the application responsibly and do not submit unlawful, harmful, or confidential content. Job listings and AI-generated suggestions should be independently verified before you act on them.</p>
        <p>The project may change or be unavailable without notice. These terms are a simple notice for a demo project and are not a substitute for legal advice.</p>
      </div>
      <Link href="/" className="inline-block mt-10 text-sm text-white/50 hover:text-white transition-colors">← Back to Rolio</Link>
    </section>
  );
}
