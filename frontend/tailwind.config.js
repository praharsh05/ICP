/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Professional Golden Theme for Government Applications
        primary: {
          50: '#FEF9E7',
          100: '#FDF5D7',
          200: '#FBEDC0',
          300: '#F8E5A8',
          400: '#F0D675',
          500: '#DAA520',
          600: '#C89519',
          700: '#A57915',
          800: '#835E11',
          900: '#62470D',
          950: '#3D2C08',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        accent: {
          50: '#FEF9E7',
          100: '#FDF5D7',
          200: '#FBEDC0',
          300: '#F8E5A8',
          400: '#F0D675',
          500: '#DAA520',
          600: '#C89519',
          700: '#A57915',
          800: '#835E11',
          900: '#62470D',
        },
        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        }
      },
      fontFamily: {
        'arabic': ['Noto Sans Arabic', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 16px rgba(0, 0, 0, 0.08)',
        'strong': '0 8px 32px rgba(0, 0, 0, 0.12)',
      }
    },
  },
  plugins: [],
}
