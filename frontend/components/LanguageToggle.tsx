'use client';

import { useLanguage } from '../contexts/LanguageContext';
import { Globe } from 'lucide-react';

export default function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-neutral-200 bg-white">
      <Globe className="w-4 h-4 text-neutral-600" />
      <div className="flex items-center gap-1 text-sm font-medium">
        <button
          onClick={() => setLanguage('en')}
          className={`px-2 py-1 rounded transition-colors ${
            language === 'en'
              ? 'bg-primary-600 text-white'
              : 'text-neutral-600 hover:text-neutral-900'
          }`}
        >
          EN
        </button>
        <span className="text-neutral-400">|</span>
        <button
          onClick={() => setLanguage('ar')}
          className={`px-2 py-1 rounded transition-colors ${
            language === 'ar'
              ? 'bg-primary-600 text-white'
              : 'text-neutral-600 hover:text-neutral-900'
          }`}
        >
          AR
        </button>
      </div>
    </div>
  );
}