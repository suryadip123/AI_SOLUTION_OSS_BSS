/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary:  '#1E6FD9',
        success:  '#22C55E',
        warning:  '#F59E0B',
        danger:   '#EF4444',
        surface:  '#0F172A',
        panel:    '#1E293B',
        muted:    '#94A3B8',
      },
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        mono:    ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
