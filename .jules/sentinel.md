## 2026-07-02 - Enforce Required JWT Secret and Mask Internal Error Details
**Vulnerability:** JWT utility defaulted to a hardcoded string `'jwt-secret'` when `JWT_SECRET_KEY` environment variable was missing, and the `login_required` decorator returned `str(e)` in JSON error responses.
**Learning:** Default fallback secrets in JWT token creation/decoding compromise token signature security if production environments forget to set `JWT_SECRET_KEY`. Leaking internal exception strings in HTTP error responses exposes stack/internal error details to unauthorized clients.
**Prevention:** Always require explicit secret environment variables by raising a `ValueError` if absent. Ensure API authentication error handlers return generic error messages without leaking internal exception details.
