# Sentinel Security Journal

## 2025-05-18 - Missing JWT Secret Fallback Prevention
**Vulnerability:** `JWTUtils` defaulted to a fallback hardcoded secret `'jwt-secret'` when the `JWT_SECRET_KEY` environment variable was not set, allowing token forging if unconfigured.
**Learning:** Fallback defaults for cryptographic keys in utility modules can silently degrade security in unconfigured or development environments.
**Prevention:** Fail fast and raise an explicit error when required security configuration variables are missing rather than providing default hardcoded secrets.
