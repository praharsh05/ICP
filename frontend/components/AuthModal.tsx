'use client';

import { useState } from 'react';
import { X, ShieldCheck, LogIn } from 'lucide-react';
import { authService } from '../utils/authService';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleLogin = async () => {
    setLoading(true);
    // Redirect to Keycloak — after login, come back to /landing so the user can enter a Unified ID
    await authService.login(`${window.location.origin}/landing`);
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
                Authenticate securely via Keycloak SSO
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
        <div className="p-8 flex flex-col items-center gap-6">
          <div className="w-16 h-16 rounded-full bg-primary-50 flex items-center justify-center">
            <ShieldCheck className="w-8 h-8 text-primary-600" />
          </div>

          <div className="text-center">
            <p className="text-neutral-700 text-sm leading-relaxed">
              You will be redirected to the ICP Identity Provider to authenticate.
              Your credentials are managed securely by Keycloak — they are never
              sent to this application.
            </p>
          </div>

          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-primary-600 hover:bg-primary-700 text-white font-medium py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <LogIn className="w-5 h-5" />
            {loading ? 'Redirecting to Keycloak…' : 'Sign in with Keycloak'}
          </button>

          <p className="text-xs text-neutral-400 text-center">
            Password reset and account management are available inside Keycloak.
          </p>
        </div>
      </div>
    </div>
  );
}
