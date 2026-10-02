## 2025-05-24 - Exception Leakage in Auth Decorators
**Vulnerability:** The `login_required` decorator leaked `str(e)` in error responses on exceptions during authentication, exposing internal database or redis error messages to unauthenticated callers.
**Learning:** Returning exception strings in error handlers leaks system internals and context on failure.
**Prevention:** Sanitize error responses returned to clients and avoid exposing `str(e)` or stack traces in API outputs.
