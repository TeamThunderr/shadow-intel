/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'shadow': {
          950: '#080c14',
          900: '#0d1424',
          800: '#111c30',
          700: '#162340',
          600: '#1e3057',
        },
        'intel': {
          500: '#3b82f6',
          400: '#60a5fa',
          300: '#93c5fd',
        },
        'danger': {
          600: '#c0392b',
          500: '#e74c3c',
          400: '#f87171',
        },
        'warn': {
          500: '#f59e0b',
          400: '#fbbf24',
        },
        'safe': {
          500: '#10b981',
          400: '#34d399',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
