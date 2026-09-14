## 2026-03-31 - JWT Secret Enforcement and Auth Exception Sanitization
**Vulnerability:** JWT authentication fell back to a default hardcoded secret key (`'jwt-secret'`), and `login_required` leaked exception details (`str(e)`) in 401 response payloads.
**Learning:** Downstream services expecting `auth.utils` must provide `JWT_SECRET_KEY` in environment variables. Unit tests for `auth.utils` require mocking the external `cache_db` package before import.
**Prevention:** Always raise errors on missing security configuration in production helpers rather than relying on weak default secrets, and never return unhandled exception details to unauthenticated API clients.
