## 2026-03-31 - [Prevent Information Leakage in Authentication Decorators]
**Vulnerability:** `login_required` decorator in `auth/utils.py` returned raw exception details `str(e)` in JSON responses to clients during JWT verification errors.
**Learning:** Returning exception strings in HTTP error responses can expose internal database URLs, system paths, or service credentials.
**Prevention:** Log exception details server-side using standard `logger.exception()` and return generic sanitised error payloads to clients.
