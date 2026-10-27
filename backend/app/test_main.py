"""
E2E-only ASGI entrypoint. Identical to app.main, plus a test-login shortcut
that mints a session token for a seeded demo role without a password (see
app/routes/test_auth.py). app/main.py — the real production entrypoint —
never imports this module and is unaffected by it.

The Playwright suite launches `uvicorn app.test_main:app` (instead of
`app.main:app`) against an isolated, throwaway database set via
BOGCHA_DB_PATH, purely so browser-driven tests can log in as any seeded role
without needing a real password.
"""
from app.main import app
from app.routes import test_auth

app.include_router(test_auth.router)
