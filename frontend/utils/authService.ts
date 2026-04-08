/**
 * Authentication service for frontend
 * Handles login, logout, token management, and API calls with authentication
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

export interface AuthError {
  message: string;
  detail?: string;
}

class AuthService {
  private tokenKey = 'auth_token';
  private userKey = 'auth_user';

  /**
   * Login with username and password
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Invalid username or password');
    }

    const data: LoginResponse = await response.json();
    this.setToken(data.access_token);
    this.setUser(data.user);
    return data;
  }

  /**
   * Logout current user
   */
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
  }

  /**
   * Get current authentication token
   */
  getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Set authentication token
   */
  setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem('isAuthenticated', 'true');
  }

  /**
   * Get current user from storage
   */
  getCurrentUser(): User | null {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem(this.userKey);
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  /**
   * Set current user
   */
  setUser(user: User): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
    if (user.email) localStorage.setItem('userEmail', user.email);
    if (user.display_name || user.username) {
      localStorage.setItem('userName', user.display_name || user.username);
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Get current user info from API
   */
  async getCurrentUserInfo(): Promise<User> {
    const token = this.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.logout();
        throw new Error('Session expired. Please login again.');
      }
      throw new Error('Failed to fetch user info');
    }

    const user: User = await response.json();
    this.setUser(user);
    return user;
  }

  /**
   * Make authenticated API request
   */
  async authenticatedFetch(
    url: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const token = this.getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/landing';
      }
      throw new Error('Session expired');
    }

    return response;
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/user-management/request-password-reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Failed to request password reset');
    }
  }

  /**
   * Refresh user roles
   */
  async refreshRoles(): Promise<User> {
    const response = await this.authenticatedFetch(
      `${API_URL}/api/v1/user-management/refresh-roles`,
      { method: 'POST' }
    );

    if (!response.ok) {
      throw new Error('Failed to refresh roles');
    }

    const user: User = await response.json();
    this.setUser(user);
    return user;
  }

  /**
   * Check if user has specific role
   */
  hasRole(role: string): boolean {
    const user = this.getCurrentUser();
    return user?.roles?.includes(role) || false;
  }

  /**
   * Check if user has any of the specified roles
   */
  hasAnyRole(...roles: string[]): boolean {
    const user = this.getCurrentUser();
    if (!user?.roles) return false;
    return roles.some(role => user.roles.includes(role));
  }
}

export const authService = new AuthService();





