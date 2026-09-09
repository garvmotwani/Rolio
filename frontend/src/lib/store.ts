/**
 * Frontend auth store and API helpers.
 *
 * Security design:
 * - Access tokens are stored in HttpOnly cookies — never in localStorage or JS.
 * - User profile data (non-sensitive) is stored in state for UI rendering.
 * - All requests include `credentials: 'include'` to send cookies.
 * - State-changing requests include the X-CSRF-Token header.
 * - The CSRF token is read from the rolio_csrf cookie (not HttpOnly).
 */
import { create } from 'zustand';
import { API_URL, apiFetch, apiPost } from './api';

interface User {
  id: number;
  email: string;
  name: string;
  is_onboarded: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  hydrated: boolean;
  setAuth: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  loadFromStorage: () => void;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, name: string) => Promise<{ success: boolean; error?: string }>;
}

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: false,
  hydrated: false,

  setAuth: (user: User) => {
    // User data stored in React state only. Tokens live in cookies set by the server.
    set({ user });
  },

  logout: () => {
    // Call backend to clear server-side session + cookies
    apiPost('/api/auth/logout').catch(() => {});
    set({ user: null });
  },

  setLoading: (loading) => set({ isLoading: loading }),

  /** On mount, try to fetch /api/auth/me using the HttpOnly cookie to verify session. */
  loadFromStorage: () => {
    if (typeof window === 'undefined') return;
    // Cookie-based auth: just try to get user info from server
    apiFetch('/api/auth/me')
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('Not authenticated');
      })
      .then((user: User) => {
        set({ user, hydrated: true });
      })
      .catch(() => {
        set({ user: null, hydrated: true });
      });
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        set({ isLoading: false });
        return { success: false, error: data.detail || 'Login failed' };
      }
      // Tokens are now in HttpOnly cookies set by the server
      get().setAuth(data.user);
      set({ isLoading: false });
      return { success: true };
    } catch {
      set({ isLoading: false });
      return { success: false, error: 'Network error' };
    }
  },

  register: async (email, password, name) => {
    set({ isLoading: true });
    try {
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, name }),
      });
      const data = await res.json();
      if (!res.ok) {
        set({ isLoading: false });
        return { success: false, error: data.detail || 'Registration failed' };
      }
      get().setAuth(data.user);
      set({ isLoading: false });
      return { success: true };
    } catch {
      set({ isLoading: false });
      return { success: false, error: 'Network error' };
    }
  },
}));

// ─── API Helpers ────────────────────────────────────────────
// The shared client lives in lib/api.ts (apiGet/apiPost/apiPut/apiDelete/
// apiFetch) and is re-exported here for existing imports.
export { apiFetch, apiGet, apiPost, apiPut, apiDelete } from './api';
