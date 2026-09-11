## 2025-05-18 - Cached User Active Status Check Bypass
**Vulnerability:** Cached user objects returned from Redis in `login_required` bypassed `is_active` validation, allowing deactivated users with active cache entries to authenticate.
**Learning:** Checking user state only on cache miss (`if not user_data:`) leaves cached entries unvalidated during subsequent requests.
**Prevention:** Always perform status checks (`is_active`) on user data regardless of whether it was retrieved from cache or database.
