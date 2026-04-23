import { defineConfig, devices } from '@playwright/test';

const CI = !!process.env['CI'];

export default defineConfig({
  testDir: './tests/e2e/specs',
  fullyParallel: false,
  workers: 1,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:3000',
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
      command: 'cd ../backend && uv run uvicorn hangman.main:app --port 8000',
      url: 'http://localhost:8000/api/v1/categories',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'pnpm dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
});
