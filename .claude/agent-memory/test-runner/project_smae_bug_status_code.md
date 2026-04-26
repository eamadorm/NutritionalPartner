---
name: SMAE APIError status_code bug fix
description: Production bug found and fixed during test coverage work — exc.status_code -> exc.code
type: project
---

`genai_errors.APIError` exposes `.code` (int), NOT `.status_code`. The production retry guard in `_call_gemini` originally used `exc.status_code`, which would raise `AttributeError` instead of comparing the HTTP status code.

Fixed in `backend/smae_engine/source_code/gemini_service/main.py` — both the `if` guard and the `logger.warning` format string.

**Why:** The wrong attribute name (`status_code` vs `code`) was copied from a different SDK (`google-api-core` exceptions use `status_code`; `google-genai` SDK uses `code`). This was the production regression described in the task.

**How to apply:** When writing tests against `genai_errors.APIError`, use `exc.code` to assert the HTTP status code. When mocking, construct with `genai_errors.APIError(429, {})` — first arg is the code.
