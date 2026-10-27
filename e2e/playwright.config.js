// @ts-check
const path = require('path');
const os = require('os');
const { defineConfig } = require('@playwright/test');
const { BACKEND_PORT, FRONTEND_PORT } = require('./ports');

const PY = process.env.LOCALAPPDATA
  ? path.join(process.env.LOCALAPPDATA, 'Programs', 'Python', 'Python312', 'python.exe')
  : 'python';

const BACKEND_DIR = path.join(__dirname, '..', 'backend');
const FRONTEND_DIR = path.join(__dirname, '..', 'frontend');

// A fresh, disposable database per run — never the real bogcha_data.db.
const TEST_DB = path.join(os.tmpdir(), `bogcha_e2e_${Date.now()}_${process.pid}.db`);

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `"${PY}" -m uvicorn app.test_main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      url: `http://127.0.0.1:${BACKEND_PORT}/`,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        ...process.env,
        BOGCHA_DB_PATH: TEST_DB,
        BOGCHA_SECRET_KEY: 'e2e-test-secret-do-not-use-in-production',
        BOGCHA_ALLOWED_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}`,
        // The sentinel telegram_bot.py treats as "no bot": without this, it
        // falls back to reading the real backend/.env file straight off
        // disk and starts polling the real, already-running production bot
        // (this actually happened once — a getUpdates 409 conflict with the
        // real bot process — before this line was added).
        TELEGRAM_BOT_TOKEN: 'SIMULATED_BOT_TOKEN',
      },
    },
    {
      command: `"${PY}" serve.py ${FRONTEND_PORT}`,
      cwd: FRONTEND_DIR,
      url: `http://127.0.0.1:${FRONTEND_PORT}/login.html`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
