/**
 * Authentication service — adapts to backend auth provider (keycloak or local).
 *
 * On init, queries GET /api/v1/auth/provider to determine the active mode.
 * Keycloak utilities are lazy-imported only when the provider is "keycloak",
 * so the app works without the keycloak-js package in local mode.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  username: string;
  email: string;
  display_name?: string;
  first_name?: string;
  last_name?: string;
  roles: string[];
  groups: string[];
  active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ── Provider detection ──────────────────────────────────────────────

let _provider: 'keycloak' | 'local' | null = null;

async function getProvider(): Promise<'keycloak' | 'local'> {
  if (_provider) return _provider;
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/provider`);
    const data = await res.json();
    _provider = data.provider === 'keycloak' ? 'keycloak' : 'local';
  } catch {
    _provider = 'local';
  }
  return _provider;
}

// ── Local token helpers ─────────────────────────────────────────────

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

function getLocalToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

function setLocalToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem('isAuthenticated', 'true');
}

function setLocalUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  if (user.email) localStorage.setItem('userEmail', user.email);
  if (user.display_name || user.username) {
    localStorage.setItem('userName', user.display_name || user.username);
  }
}

function getLocalUser(): User | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

function clearLocal(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('isAuthenticated');
  localStorage.removeItem('userEmail');
  localStorage.removeItem('userName');
}

// ── Auth service ────────────────────────────────────────────────────

class AuthService {
  /**
   * For PROTECTED pages — ensures the user is authenticated.
   * Keycloak: redirects to Keycloak login if not authenticated.
   * Local: returns true if a token exists, false otherwise.
   */
  async initProtected(): Promise<boolean> {
    const provider = await getProvider();
    if (provider === 'keycloak') {
      const { initKeycloakRequired } = await import('./keycloak');
      return initKeycloakRequired();
    }
    return !!getLocalToken();
  }

  /**
   * For PUBLIC pages — passive check, no redirect.
   */
  async initPassive(): Promise<boolean> {
    const provider = await getProvider();
    if (provider === 'keycloak') {
      const { initKeycloakPassive } = await import('./keycloak');
      return initKeycloakPassive();
    }
    return !!getLocalToken();
  }

  /**
   * Login.
   * Keycloak: redirects to Keycloak login page.
   * Local: posts username/password to backend, stores JWT.
   */
  async login(usernameOrRedirectUri?: string, password?: string): Promise<LoginResponse | void> {
    const provider = await getProvider();

    if (provider === 'keycloak') {
      const { keycloakLogin } = await import('./keycloak');
      await keycloakLogin(usernameOrRedirectUri ?? `${window.location.origin}/app`);
      return;
    }

    // Local mode — username + password required
    if (!usernameOrRedirectUri || !password) {
      throw new Error('Username and password are required for local login');
    }

    const formData = new URLSearchParams();
    formData.append('username', usernameOrRedirectUri);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Invalid username or password');
    }

    const data: LoginResponse = await response.json();
    setLocalToken(data.access_token);
    setLocalUser(data.user);
    return data;
  }

  /**
   * Logout.
   */
  async logout(): Promise<void> {
    const provider = await getProvider();
    if (provider === 'keycloak') {
      const { keycloakLogout } = await import('./keycloak');
      await keycloakLogout(`${window.location.origin}/landing`);
      return;
    }
    clearLocal();
  }

  /**
   * Synchronous auth check — only reliable after initProtected/initPassive.
   */
  isAuthenticated(): boolean {
    // Quick sync check — provider detection may not have run yet
    if (_provider === 'keycloak') {
      try {
        // Dynamic require would fail at build time, so check lazily
        return false; // caller should use initProtected/initPassive for keycloak
      } catch { return false; }
    }
    return !!getLocalToken();
  }

  /**
   * Get the current access token.
   */
  async getToken(): Promise<string | null> {
    const provider = await getProvider();
    if (provider === 'keycloak') {
      const { getAccessToken } = await import('./keycloak');
      return getAccessToken();
    }
    return getLocalToken();
  }

  /**
   * Fetch current user profile from the backend.
   */
  async getCurrentUserInfo(): Promise<User> {
    const token = await this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      if (response.status === 401) {
        clearLocal();
        throw new Error('Session expired. Please login again.');
      }
      throw new Error('Failed to fetch user info');
    }

    const user: User = await response.json();
    setLocalUser(user);
    return user;
  }

  /**
   * Make an authenticated fetch request.
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = await this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });

    if (response.status === 401) {
      clearLocal();
      if (typeof window !== 'undefined') {
        window.location.href = '/landing';
      }
      throw new Error('Session expired');
    }

    return response;
  }

  /**
   * Get user's current roles.
   */
  async getRoles(): Promise<string[]> {
    const provider = await getProvider();
    if (provider === 'keycloak') {
      try {
        const { getKeycloak } = await import('./keycloak');
        const kc = await getKeycloak();
        const realmAccess = (kc.tokenParsed as any)?.realm_access ?? {};
        const allRoles: string[] = realmAccess.roles ?? [];
        const systemRoles = new Set(['offline_access', 'uma_authorization']);
        return allRoles.filter(
          (r: string) => !systemRoles.has(r) && !r.startsWith('default-roles-'),
        );
      } catch { return []; }
    }
    const user = getLocalUser();
    return user?.roles ?? [];
  }

  /**
   * Check if user has a specific role.
   */
  async hasRole(role: string): Promise<boolean> {
    const roles = await this.getRoles();
    return roles.includes(role);
  }

  /**
   * Get the current user from local storage (sync, no API call).
   */
  getCurrentUser(): User | null {
    return getLocalUser();
  }
}

export const authService = new AuthService();
