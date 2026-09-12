## 2025-09-12 - Prevent Error Details Leakage in Auth Decorators
**Vulnerability:** Exception details (`str(e)`) were returned in HTTP 401 responses inside the `login_required` decorator, leaking internal error messages and system internals to unauthenticated users.
**Learning:** Returning exception text in authentication failure handlers risks exposing sensitive database or internal application state to attackers.
**Prevention:** Always fail securely by returning generic error messages (e.g. `{"error": "Unauthorized"}`) on authentication failures.
