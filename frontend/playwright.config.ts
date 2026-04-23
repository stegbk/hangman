import { defineConfig, devices } from '@playwright/test';

const CI = !!process.env['CI'];

// Port config — override via HANGMAN_BACKEND_PORT / HANGMAN_FRONTEND_PORT if
// the canonical 8000/3000 are taken (e.g. SSH tunnel on :8000). Vite's
// vite.config.ts reads the same env vars so the dev servers + proxy agree.
const backendPort = process.env.HANGMAN_BACKEND_PORT ?? '8000';
const frontendPort = process.env.HANGMAN_FRONTEND_PORT ?? '3000';

export default defineConfig({
  testDir: './tests/e2e/specs',
  fullyParallel: false,
  workers: 1,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://localhost:${frontendPort}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `cd ../backend && uv run uvicorn hangman.main:app --port ${backendPort}`,
      url: `http://localhost:${backendPort}/api/v1/categories`,
      reuseExistingServer: true,
      timeout: 120000,
      env: {
        HANGMAN_BACKEND_PORT: backendPort,
      },
    },
    {
      command: 'pnpm dev',
      url: `http://localhost:${frontendPort}`,
      reuseExistingServer: true,
      timeout: 120000,
      env: {
        HANGMAN_BACKEND_PORT: backendPort,
        HANGMAN_FRONTEND_PORT: frontendPort,
      },
    },
  ],
});
