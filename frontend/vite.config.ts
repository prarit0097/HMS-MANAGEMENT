import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: { host: '127.0.0.1', proxy: { '/api': loadEnv(mode, '.', 'HMS_').HMS_API_TARGET || 'http://127.0.0.1:8000' } },
  preview: { host: '127.0.0.1' },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], globals: true },
}));
