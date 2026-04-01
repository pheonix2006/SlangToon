import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['../tests/frontend/unit/setup.ts'],
    include: ['../tests/frontend/unit/**/*.{test,spec}.{ts,tsx}'],
  },
});
