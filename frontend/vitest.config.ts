import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Playwright specs live under tests/e2e/ and use Playwright's test/expect,
    // which conflicts with Vitest's globals. Run them via `pnpm exec playwright
    // test`, not vitest.
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
});
