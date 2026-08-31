## 2026-08-31 - JWT Secret Hardcoded Fallback
**Vulnerability:** JWT authentication fallback key `'jwt-secret'` was hardcoded when `JWT_SECRET_KEY` env var was missing, permitting token forgery.
**Learning:** Default fallbacks for secret credentials in utility classes can lead to accidental deployment with known default keys.
**Prevention:** Fail fast by raising exceptions (or returning validation failure) when required cryptographic secrets are missing from configuration.
