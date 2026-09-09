import { NextResponse, type NextRequest } from 'next/server';

/**
 * Force HTTPS in production.
 *
 * Enabled when FORCE_HTTPS=true (set it in the deployment environment — the
 * Dockerfile build stage does NOT need it; this runs at request time).
 * Requests arriving over plain http:// are 308-redirected to https://.
 *
 * The scheme is trusted only when behind the platform's TLS terminator:
 * - hosted platforms (Vercel/Render/Fly) set x-forwarded-proto themselves;
 * - self-hosted: put nginx/Caddy in front and only allow HTTPS there.
 * /api/health is exempt so load-balancer probes over HTTP don't 307.
 */
const FORCE_HTTPS = process.env.FORCE_HTTPS === 'true';

export function middleware(request: NextRequest) {
  if (!FORCE_HTTPS) return NextResponse.next();

  const proto = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '');
  const isHealth = request.nextUrl.pathname.startsWith('/api/health');

  if (proto === 'http' && !isHealth) {
    const httpsUrl = new URL(request.nextUrl.toString());
    httpsUrl.protocol = 'https:';
    return NextResponse.redirect(httpsUrl, 308);
  }
  return NextResponse.next();
}

export const config = {
  // Skip static assets — no need to run the middleware for them.
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
