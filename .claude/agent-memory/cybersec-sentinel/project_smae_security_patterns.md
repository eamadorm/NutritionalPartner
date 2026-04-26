---
name: SMAE Engine Security Patterns
description: Known security findings, controls, and risk areas specific to the SMAE engine Cloud Run service
type: project
---

SMAE engine is a Cloud Run service (Vertex AI + BigQuery) for PDF nutritional data ingestion. Authentication is IAM-enforced (no allUsers). ADC used exclusively.

**Critical regression risk — wrong attribute name on APIError**: The google-genai SDK stores the HTTP status code as `exc.code`, NOT `exc.status_code`. Any code checking `exc.status_code` will always receive `None`, making every conditional against it evaluate incorrectly. This caused the retry guard in `_call_gemini` to be silently broken. Always verify against the installed SDK source at `backend/.venv/lib/python3.13/site-packages/google/genai/errors.py`.

**Why:** Confirmed live via `uv run python` — `getattr(obj, 'status_code', None)` returns `None` on an `APIError(429, ...)` instance. The attribute `code` is the correct one (set in `__init__`).

**How to apply:** Flag any future code that references `exc.status_code` on a `genai_errors.APIError` as a High/Critical correctness + security bug. Correct form is `exc.code`.

**Retry amplification risk**: `max_retries` and `max_parallel_workers` in `GeminiSettings` have only lower bounds (`ge=`), no upper bounds (`le=`). An operator setting these to arbitrarily large values via env vars could exhaust Cloud Run concurrency or trigger excessive Gemini API spend. Recommend adding `le=10` on `max_retries` and `le=20` on `max_parallel_workers`.

**run_in_executor thread leak**: `smae_handler` in `main.py` uses `loop.run_in_executor(None, ...)` with no `asyncio.wait_for` timeout wrapper. If Cloud Run terminates the HTTP connection, the background thread running `pipeline.run()` continues executing (potentially issuing multiple Gemini calls) until the Cloud Run instance is eventually killed. This is a resource cost issue, not a data confidentiality issue.

**Error log scope**: Warning log in `_call_gemini` emits `exc.status_code` (actually `None` due to above bug) and `exc.__class__.__name__` only. No message, details, or response body is logged — acceptable information disclosure posture once the attribute name is fixed.

**Security gate result (as of 2026-04-26)**: FAIL — 1 High finding (broken retry guard / wrong attribute). Gate requires 0 High.
