/**
 * Indian currency formatting — ₹ with lakh/crore units (the standard
 * notation for Indian salary figures).
 *
 * All salary values across the app are annual INR.
 */

/** Format a single amount: 450000 → "₹45L", 1200000 → "₹12L", 15000000 → "₹1.5Cr" */
export function formatINR(n: number): string {
  if (!n) return '';
  if (n >= 10_000_000) {
    const cr = n / 10_000_000;
    return `₹${cr % 1 === 0 ? cr : cr.toFixed(1).replace(/\.0$/, '')}Cr`;
  }
  if (n >= 100_000) {
    const l = n / 100_000;
    return `₹${l % 1 === 0 ? l : l.toFixed(1).replace(/\.0$/, '')}L`;
  }
  return `₹${n.toLocaleString('en-IN')}`;
}

/** Format a salary range: (3200000, 5500000) → "₹32L – ₹55L/yr" */
export function formatINRRange(min: number, max: number, suffix = '/yr'): string {
  if (!min && !max) return 'Not specified';
  if (min && max) return `${formatINR(min)} – ${formatINR(max)}${suffix}`;
  if (min) return `From ${formatINR(min)}${suffix}`;
  return `Up to ${formatINR(max!)}${suffix}`;
}

/** Compact LPA display for charts: 3200000 → "32", 3500000 → "3.5Cr"? no — "35L" */
export function inrCompact(n: number): string {
  return formatINR(n);
}
