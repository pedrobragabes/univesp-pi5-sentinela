import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
const localPython = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
const python = process.env.SENTINELA_PYTHON || (existsSync(localPython) ? localPython : 'python');
export default defineConfig({
  testDir: './e2e', workers: 1, forbidOnly: Boolean(process.env.CI), retries: process.env.CI ? 1 : 0,
  use: { baseURL: 'http://127.0.0.1:3486', reducedMotion: 'reduce', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 } } },
    { name: 'compact', use: { viewport: { width: 320, height: 740 } } },
  ],
  webServer: { command: `"${python}" -m scripts.browser_server`, url: 'http://127.0.0.1:3486/api/v1/status', reuseExistingServer: false },
});
