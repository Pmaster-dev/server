## 2026-03-29 - Hardcoded JWT Secret Fallback and Sensitive Error Leakage
**Vulnerability:** JWT token handling used a hardcoded fallback secret (`jwt-secret`) when `JWT_SECRET_KEY` environment variable was unconfigured, and authentication decorator `login_required` leaked exception details (`details: str(e)`) in HTTP 401 responses.
**Learning:** Fallback secret values in authentication mechanisms allow token forgery if configuration is omitted in production, while returning detailed exception messages exposes backend internal state to unauthorized clients.
**Prevention:** Require explicit configuration for secrets by throwing explicit configuration errors on startup/access when environment variables are missing, and sanitize error responses sent to API clients.
