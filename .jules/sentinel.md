## 2025-02-28 - External Ecosystem Module Dependency Mocking in Auth
**Vulnerability:** Information disclosure via `str(e)` leakage in Flask `login_required` error responses.
**Learning:** `auth/utils.py` imports `cache_db` at module top-level, which is an external dependency not present in this standalone repository. Unit tests for `auth/utils.py` must mock `cache_db` in `sys.modules` before importing `auth.utils`.
**Prevention:** Always mock `cache_db`, `cache_db.redis_client`, and `cache_db.models` in test fixtures before importing `auth.utils` to prevent `ModuleNotFoundError`.
