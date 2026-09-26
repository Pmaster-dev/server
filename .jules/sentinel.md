## 2026-07-02 - Enforce mandatory JWT secret and eliminate auth error leakage
**Vulnerability:** JWT utility defaulted to a hardcoded string ('jwt-secret') when `JWT_SECRET_KEY` was missing from environment, and `login_required` decorator returned `str(e)` exception details to clients upon auth failure.
**Learning:** Defaulting secret parameters to fallback strings allows production deployments to run insecurely without notice. Additionally, returning internal exception messages in error responses leaks internal state and connection parameters.
**Prevention:** Always raise explicit runtime configuration errors when crucial environment secrets are missing, and catch exceptions at API boundaries returning sanitized error messages without raw exception strings.
