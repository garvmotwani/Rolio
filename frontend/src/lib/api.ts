/**
 * Rolio frontend API client — single shared module for all backend requests.
 *
 * Every helper:
 * - uses NEXT_PUBLIC_API_URL (falls back to localhost:8001 for local dev),
 * - sends cookies (`credentials: 'include'`) for HttpOnly cookie auth,
 * - attaches the X-CSRF-Token header on state-changing requests,
 * - surfaces backend error details consistently.
 *
 * Silent session refresh:
 * - 401 responses trigger an automatic token refresh + retry (once).
 * - A proactive timer refreshes before the access token expires so users
 *   never see a flash of "not authenticated".
 * - A lock prevents multiple concurrent refresh attempts.
 *
 * NOTE: no access/refresh token is ever stored or read in JS — auth lives
 * entirely in HttpOnly cookies; only the non-HttpOnly CSRF cookie is read.
 */

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001').trim();

// ─── CSRF ────────────────────────────────────────────────────

function getCsrfToken(): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/(?:^|; )rolio_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

export function authHeaders(json = true): HeadersInit {
  const headers: Record<string, string> = {
    'X-CSRF-Token': getCsrfToken(),
  };
  if (json) headers['Content-Type'] = 'application/json';
  return headers;
}

// ─── Silent Session Refresh ──────────────────────────────────

/** Access token lifetime in minutes (must stay in sync with backend). */
const ACCESS_EXPIRE_MINUTES = 30;
/** Refresh 5 minutes before expiry so users never see a flash. */
const REFRESH_BUFFER_MS = 5 * 60 * 1000;
/** Proactive refresh interval (check every 60 seconds). */
const PROACTIVE_CHECK_INTERVAL_MS = 60 * 1000;

let refreshPromise: Promise<boolean> | null = null;
let proactiveTimer: ReturnType<typeof setInterval> | null = null;
let lastRefreshTime = 0;

/**
 * Attempt to refresh the session by hitting POST /api/auth/refresh.
 * Returns true if the refresh succeeded, false otherwise.
 * Uses a lock so concurrent callers share the same refresh attempt.
 */
async function tryRefreshSession(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_URL}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': getCsrfToken(),
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        lastRefreshTime = Date.now();
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Proactive refresh: refresh before the access token expires.
 * Runs every 60s. If we're within the buffer window of the last known
 * refresh, proactively refresh now.
 */
function startProactiveRefresh() {
  if (proactiveTimer || typeof window === 'undefined') return;

  const intervalMs = ACCESS_EXPIRE_MINUTES * 60 * 1000 - REFRESH_BUFFER_MS;
  lastRefreshTime = Date.now();

  proactiveTimer = setInterval(async () => {
    const elapsed = Date.now() - lastRefreshTime;
    if (elapsed >= intervalMs) {
      await tryRefreshSession();
    }
  }, PROACTIVE_CHECK_INTERVAL_MS);
}

function stopProactiveRefresh() {
  if (proactiveTimer) {
    clearInterval(proactiveTimer);
    proactiveTimer = null;
  }
}

// Start proactive refresh when the module loads in the browser
if (typeof window !== 'undefined') {
  startProactiveRefresh();
}

// ─── Core Fetch ──────────────────────────────────────────────

/** Low-level fetch with credentials + CSRF. Returns the raw Response. */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const method = (options.method || 'GET').toUpperCase();
  const isMutating = !['GET', 'HEAD', 'OPTIONS'].includes(method);

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  if (isMutating) {
    headers['X-CSRF-Token'] = getCsrfToken();
  }
  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });

  // ── Silent refresh on 401 ──
  if (res.status === 401 && path !== '/api/auth/refresh' && path !== '/api/auth/login' && path !== '/api/auth/register') {
    const refreshed = await tryRefreshSession();
    if (refreshed) {
      // Retry the original request with fresh cookies
      const retryHeaders: Record<string, string> = {
        ...(options.headers as Record<string, string> || {}),
      };
      if (isMutating) {
        retryHeaders['X-CSRF-Token'] = getCsrfToken();
      }
      if (options.body && typeof options.body === 'string' && !retryHeaders['Content-Type']) {
        retryHeaders['Content-Type'] = 'application/json';
      }
      res = await fetch(`${API_URL}${path}`, {
        ...options,
        credentials: 'include',
        headers: retryHeaders,
      });
    }
    // If refresh failed, the 401 propagates and the caller handles it
  }

  return res;
}

/** Extract a readable message from a failed Response. */
export async function errorMessage(res: Response, fallback = 'Request failed'): Promise<string> {
  try {
    const data = await res.json();
    return data?.detail || fallback;
  } catch {
    return fallback;
  }
}

// ─── JSON helpers ───────────────────────────────────────────

export async function apiGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path);
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: 'PUT',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await apiFetch(path, { method: 'DELETE' });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

// ─── Binary download helper (CSV exports) ───────────────────

export async function apiDownload(path: string, filename: string): Promise<void> {
  const res = await apiFetch(path);
  if (!res.ok) throw new Error(await errorMessage(res, 'Download failed'));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── Streaming POST helper (NDJSON token streams) ───────────

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone?: (final: unknown) => void;
}

/**
 * POST an NDJSON stream request. Calls onToken for each streamed token and
 * onDone with the final payload ({type: 'done', ...}) when the stream ends.
 */
export async function apiStream(
  path: string,
  body: unknown,
  { onToken, onDone }: StreamCallbacks,
): Promise<void> {
  const res = await apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
  if (!res.ok) throw new Error(await errorMessage(res, 'Stream failed'));

  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('ndjson') || !res.body) {
    // Non-streaming fallback: treat the whole body as the final result
    const data = await res.json().catch(() => null);
    if (onDone) onDone(data);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const data = JSON.parse(line);
        if (data.type === 'token' && data.token) {
          onToken(data.token);
        } else if (data.type === 'done') {
          if (onDone) onDone(data);
        } else if (data.token) {
          // Legacy format: bare {token} lines
          onToken(data.token);
        } else if (data.done && data.full) {
          if (onDone) onDone(data);
        }
      } catch {
        /* skip malformed lines */
      }
    }
  }
}

// ─── File upload helper ─────────────────────────────────────

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiFetch(path, { method: 'POST', body: formData });
  if (!res.ok) throw new Error(await errorMessage(res, 'Upload failed'));
  return res.json();
}

// ─── Session utilities ───────────────────────────────────────

/** Manually trigger a session refresh (e.g., after profile update). */
export async function refreshSession(): Promise<boolean> {
  return tryRefreshSession();
}

/** Stop the proactive refresh timer (call on logout). */
export function teardownSessionRefresh(): void {
  stopProactiveRefresh();
  lastRefreshTime = 0;
}

// ─── Legacy compatibility export ────────────────────────────

export const api = { get: apiGet, post: apiPost, put: apiPut, delete: apiDelete };
