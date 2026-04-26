---
name: SMAE Engine Testing Conventions
description: Testing framework, file location, patterns, and constraints for the SMAE engine test suite
type: project
---

Tests live at `/workspaces/NutritionalPartner/tests/backend/smae_engine/test_engine.py`.
Run with: `cd backend && uv run pytest ../tests/backend/smae_engine/ -v`
Framework: pytest with pytest-mock (mocker fixture). No pytest-asyncio needed — all SMAE code is synchronous.

**GeminiSettings field minimums to respect in tests:**
- `retry_base_delay_s` >= 0.1
- `retry_max_delay_s` >= 1.0
- `batch_result_timeout_s` >= 10.0
Do not pass sub-minimum values; use defaults and mock `time.sleep` instead.

**Mocking `_process_batches_parallel` timeout:**
Cannot set `batch_result_timeout_s` below 10 in tests. Inject FutureTimeoutError by patching `ThreadPoolExecutor` and `as_completed` directly so `future.result()` raises immediately.

**Why:** These constraints come from Pydantic `ge=` validators on `GeminiSettings` (BaseSettings). Discovered when writing retry/timeout tests for the `_call_gemini` exception handling fix.

**How to apply:** When writing tests for `_call_gemini` or `_process_batches_parallel`, always mock `time.sleep` to avoid real delays, and satisfy Pydantic field constraints using allowed minimum values.
