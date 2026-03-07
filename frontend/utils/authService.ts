/**
 * Authentication service — Keycloak OIDC edition.
 */

import {
  getKeycloak,
  initKeycloakRequired,
  initKeycloakPassive,
  keycloakLogout,
  getAccessToken,
  isKeycloakAuthenticated,
} from './keycloak';

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

class AuthService {
  /**
   * For PROTECTED pages (/app, /tree, etc.)
   * Uses `login-required` — redirects to Keycloak if not authenticated.
   * Returns true when authenticated (after code exchange or existing session).
   */
  async initProtected(): Promise<boolean> {
    return initKeycloakRequired();
  }

  /**
   * For PUBLIC pages (/landing).
   * Passive init — no redirect. Returns true if already authenticated.
   */
  async initPassive(): Promise<boolean> {
    return initKeycloakPassive();
  }

  /**
   * Redirect to the Keycloak login page.
   */
  async login(redirectUri?: string): Promise<void> {
    const { keycloakLogin } = await import('./keycloak');
    await keycloakLogin(redirectUri ?? `${window.location.origin}/app`);
  }

  /**
   * Redirect to the Keycloak logout endpoint.
   */
  async logout(): Promise<void> {
    await keycloakLogout(`${window.location.origin}/landing`);
  }

  /**
   * Synchronous check — only reliable after initProtected/initPassive has resolved.
   */
  isAuthenticated(): boolean {
    return isKeycloakAuthenticated();
  }

  /**
   * Return the current Keycloak access token (auto-refreshed if near expiry).
   */
  async getToken(): Promise<string | null> {
    return getAccessToken();
  }

  /**
   * Fetch current user profile from the backend (/api/v1/auth/me).
   */
  async getCurrentUserInfo(): Promise<User> {
    const token = await this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      if (response.status === 401) {
        await this.login();
        throw new Error('Session expired — redirecting to login');
      }
      throw new Error('Failed to fetch user info');
    }

    return response.json();
  }

  /**
   * Make an authenticated fetch request.
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = await this.getToken();
    if (!token) {
      await this.login();
      throw new Error('Not authenticated');
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });

    if (response.status === 401) {
      await this.login();
      throw new Error('Session expired');
    }

    return response;
  }

  async getRoles(): Promise<string[]> {
    try {
      const kc = await getKeycloak();
      const realmAccess = (kc.tokenParsed as any)?.realm_access ?? {};
      const allRoles: string[] = realmAccess.roles ?? [];
      const systemRoles = new Set(['offline_access', 'uma_authorization']);
      return allRoles.filter(
        (r: string) => !systemRoles.has(r) && !r.startsWith('default-roles-'),
      );
    } catch {
      return [];
    }
  }

  async hasRole(role: string): Promise<boolean> {
    const roles = await this.getRoles();
    return roles.includes(role);
  }
}

export const authService = new AuthService();
