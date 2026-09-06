## 2025-02-23 - Prevent Exception Details Leakage in Auth Responses
**Vulnerability:** `auth/utils.py`'s `@login_required` decorator exposed internal exception strings (`details: str(e)`) to clients upon authentication failure, risking exposure of database/cache state or internal implementation details.
**Learning:** Returning `str(e)` in Flask error responses provides an easy path for information disclosure when third-party libraries or DB connections fail during auth verification.
**Prevention:** Always log exception details internally via standard logging (`logger.warning` / `logger.error`) and return sanitized generic error responses (e.g. `{'error': 'Unauthorized'}`) to clients.
