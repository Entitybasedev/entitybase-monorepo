import { defineConfig } from '@playwright/test'

const API_URL = process.env.API_URL || 'http://localhost:8083'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '8085'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
  },
  globalSetup: './setup/global-setup.js',
  webServer: {
    command: 'npm run dev',
    cwd: '../entitybase-frontend',
    url: `http://localhost:${FRONTEND_PORT}`,
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
