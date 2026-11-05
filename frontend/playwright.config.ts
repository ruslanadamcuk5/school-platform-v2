import { defineConfig } from '@playwright/test';

const authFile = 'e2e/.auth/user.json';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL:
      process.env.PILOT_BASE_URL ?? 'https://school-platform-v2.alwaysdata.net',
    channel: 'msedge',
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'off',
    viewport: { width: 1366, height: 900 },
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'pilot',
      testMatch: /.*\.spec\.ts/,
      dependencies: ['setup'],
      use: { storageState: authFile },
    },
  ],
});
