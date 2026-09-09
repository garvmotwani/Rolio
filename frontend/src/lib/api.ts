/**
 * Rolio frontend API client — single shared module for all backend requests.
 *
 * Every helper:
 * - uses NEXT_PUBLIC_API_URL (falls back to localhost:8001 for local dev),
 * - sends cookies (`credentials: 'include'`) for HttpOnly cookie auth,
 * - attaches the X-CSRF-Token header on state-changing requests,
 * - surfaces backend error details consistently.
 *
 * NOTE: no access/refresh token is ever stored or read in JS — auth lives
 * entirely in HttpOnly cookies; only the non-HttpOnly CSRF cookie is read.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

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

  return fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });
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

// ─── Legacy compatibility export ────────────────────────────

export const api = { get: apiGet, post: apiPost, put: apiPut, delete: apiDelete };
