import { defineConfig } from '@playwright/test'

const API_URL = process.env.API_URL || 'http://localhost:8083'
const FRONTEND_PORT = process.env.FRONTEND_PORT || '8085'

export default defineConfig({
  testDir: './tests',
  // Saving an entity reloads it, which takes several round trips; under
  // parallel load that regularly exceeds the 5s default
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // The backend occasionally takes longer than the per-test timeout while
  // saving an entity under parallel load, so retry once before failing
  retries: 1,
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
