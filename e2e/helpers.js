const { BACKEND_PORT } = require('./ports');

const API_BASE = `http://127.0.0.1:${BACKEND_PORT}/api/v1`;

// Logs a page in as a seeded demo role via the test-only token endpoint
// (app/routes/test_auth.py), skipping the real login form entirely. No
// password exists anywhere in this flow: the token is minted straight from
// a known seeded user id, the same way backend/tests/conftest.py does it.
async function loginAs(page, role) {
  const res = await page.request.post(`${API_BASE}/test/login`, {
    data: { role },
  });
  if (!res.ok()) {
    throw new Error(`test/login failed for role "${role}": ${res.status()}`);
  }
  const { token } = await res.json();

  await page.addInitScript(
    ([t, apiBase]) => {
      window.__BOGCHA_API_BASE__ = apiBase;
      try {
        localStorage.setItem('bogcha_token', t);
      } catch (e) {}
    },
    [token, API_BASE]
  );

  // Wait for the real /auth/me round trip, not just for #currentUserName to
  // be non-empty — the element already has placeholder text in the static
  // HTML, so that check passes even when the fetch fails (e.g. CORS) and
  // nothing real ever loaded.
  const [meResponse] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith('/auth/me') && r.request().method() === 'GET'),
    page.goto('/index.html'),
  ]);
  if (!meResponse.ok()) {
    throw new Error(`/auth/me returned ${meResponse.status()} while logging in as "${role}"`);
  }
}

module.exports = { loginAs, API_BASE };
