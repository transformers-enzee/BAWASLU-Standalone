import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(__dirname, '../backend');
const adminPassword = ['e2e','admin','local'].join('-');

export default defineConfig({
  testDir: './e2e',
  testMatch: ['stable.spec.js'],
  timeout: 45000,
  expect: { timeout: 8000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'rm -f playwright-ci.db && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        ...process.env,
        DATABASE_URL: 'sqlite:///./playwright-ci.db',
        BAWASLU_BOOTSTRAP_ADMIN_EMAIL: 'admin@bawaslu.local',
        BAWASLU_BOOTSTRAP_ADMIN_PASSWORD: adminPassword,
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1',
      cwd: __dirname,
      url: 'http://127.0.0.1:5173/login',
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
