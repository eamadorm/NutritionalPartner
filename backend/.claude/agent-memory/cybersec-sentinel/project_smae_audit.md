---
name: SMAE Engine Stage 2 Security Audit Results
description: Security audit findings for SMAE Engine deployment — key patterns and residual risks to track for regression prevention
type: project
---

SMAE Engine Stage 2 security audit completed (2026-04-26). Gate result: PASS (0 Urgent, 0 High, 2 Medium, 4 Low).

Key findings to prevent regression:
- GCS bucket (nutritional-data-sources) has no explicit `public_access_prevention = "enforced"` in shared_resources/main.tf. CFF gcs module defaults may protect this, but it is not declared explicitly.
- BQ dataset has no explicit `encryption_configuration` (CMEK). Google-managed keys are used by default — acceptable for MVP but flagged for compliance review.
- Cloud Function IAM block `"roles/cloudfunctions.invoker" = []` has an empty member list. This appears intentional (no invokers declared in Terraform, relying on --no-allow-unauthenticated in CD), but creates a gap: Terraform does not explicitly enumerate which service accounts/principals CAN invoke the function. Access must be granted out-of-band.
- cloudbuild-cd.yaml uses `$REGION` (built-in) not `$_REGION` (user-defined substitution) on line 42. With ALLOW_LOOSE, silently passes --region= empty to gcloud deploy.
- No application-level rate limiting (slowapi) on smae_handler. Project security gate requires it for MVP.
- roles/bigquery.dataEditor is project-scoped, granting delete capability across all BQ datasets — not scoped to the specific table.
- roles/aiplatform.user is project-scoped — no VPC-SC or condition scoping.

**Why:** Recorded to prevent these patterns from reappearing in future deployables and to track remediation status.
**How to apply:** When reviewing future Cloud Function deployables, verify rate limiting, explicit public_access_prevention, invoker IAM member list, and CD YAML substitution variable naming.
