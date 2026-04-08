'use client';

import { useState, useEffect } from 'react';
import { X, ShieldCheck, LogIn, Lock } from 'lucide-react';
import { authService } from '../utils/authService';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  const [provider, setProvider] = useState<'keycloak' | 'local' | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetch(`${API_URL}/api/v1/auth/provider`)
        .then((res) => res.json())
        .then((data) => setProvider(data.provider === 'keycloak' ? 'keycloak' : 'local'))
        .catch(() => setProvider('local'));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleKeycloakLogin = async () => {
    setLoading(true);
    await authService.login(`${window.location.origin}/landing`);
  };

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await authService.login(username, password);
      if (onSuccess) {
        onSuccess();
      } else {
        window.location.href = '/app';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">Access System</h2>
              <p className="text-primary-100 text-sm mt-1">
                {provider === 'keycloak'
                  ? 'Authenticate securely via Keycloak SSO'
                  : 'Login with your credentials'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {provider === null && (
            <div className="text-center text-neutral-500 py-4">Loading...</div>
          )}

          {provider === 'keycloak' && (
            <div className="flex flex-col items-center gap-6 py-2">
              <div className="w-16 h-16 rounded-full bg-primary-50 flex items-center justify-center">
                <ShieldCheck className="w-8 h-8 text-primary-600" />
              </div>
              <p className="text-neutral-700 text-sm text-center leading-relaxed">
                You will be redirected to the ICP Identity Provider to authenticate.
              </p>
              <button
                onClick={handleKeycloakLogin}
                disabled={loading}
                className="w-full flex items-center justify-center gap-3 bg-primary-600 hover:bg-primary-700 text-white font-medium py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <LogIn className="w-5 h-5" />
                {loading ? 'Redirecting...' : 'Sign in with Keycloak'}
              </button>
            </div>
          )}

          {provider === 'local' && (
            <form onSubmit={handleLocalLogin} className="space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Enter your username"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full px-4 py-3 pl-11 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="Enter your password"
                  />
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
