# Security Audit: enterprise-ecommerce-api

A self-conducted security review of this API, with a working proof-of-concept, a
fix, and a regression test for each finding. Every row is reproducible: run the
listed test, then `git revert` the fix commit and watch it fail.

- **Audited at commit:** `b20c642`
- **Regression tests:** `pytest -m security` (16 tests). Full suite: 26 → 42 passing.
- **CI gate:** `.github/workflows/security.yml` blocks any merge with a HIGH+ finding.

## Findings

| ID | Finding | CWE | Severity | Fix | Regression test |
|----|---------|-----|----------|-----|-----------------|
| ECOM-01 | Anonymous registration grants admin, exposing every customer's email and orders | [CWE-269](https://cwe.mitre.org/data/definitions/269.html) | **Critical** | `e2db231` | `test_register_rejects_is_admin_field`, `test_order_summary_scopes_to_owner` |
| ECOM-02 | App boots with a known placeholder JWT signing key | [CWE-798](https://cwe.mitre.org/data/definitions/798.html) | High | `9f9a9f8` | `test_settings_rejects_known_placeholder_secret`, `test_settings_requires_secret_key` |
| ECOM-03 | JWTs verified without issuer/audience; forgeable across services | [CWE-347](https://cwe.mitre.org/data/definitions/347.html) | High | `2f2d35b` | `test_token_with_wrong_audience_is_rejected`, `test_token_signed_with_wrong_key_is_rejected` |
| ECOM-04 | Malformed token subject returns HTTP 500, a validity oracle | [CWE-703](https://cwe.mitre.org/data/definitions/703.html) | Medium | `2f2d35b` | `test_malformed_subject_returns_401_not_500` |
| ECOM-05 | No rate limiting on login (online password guessing) | [CWE-307](https://cwe.mitre.org/data/definitions/307.html) | Medium | `72d381c` | `test_login_locks_out_after_repeated_failures` |
| ECOM-06 | CORS allowed any origin with credentials | [CWE-942](https://cwe.mitre.org/data/definitions/942.html) | Medium | `72d381c` | `test_cors_rejects_unlisted_origin` |
| ECOM-07 | Registration confirmed which emails/usernames exist | [CWE-204](https://cwe.mitre.org/data/definitions/204.html) | Low | `72d381c` | `test_duplicate_registration_does_not_confirm_account` |
| ECOM-08 | Container ran `--reload`, unpinned base, no healthcheck; compose bind mount defeated non-root user | [CWE-16](https://cwe.mitre.org/data/definitions/16.html) | Low | `72d381c` | verified by `trivy config` in CI |

## ECOM-01, in detail (the headline)

**The flaw.** `UserCreate` exposed an `is_admin` field, and `create_user` copied it
straight into the `User` row. Nothing checked it. So:

```
POST /api/v1/auth/register   {"username": "attacker", ..., "is_admin": true}
```

created an administrator with no authentication at all.

**The impact, not just the flaw.** Admin is not cosmetic here. `GET /orders/summary`
returns, for every order in the system, the customer's email address and order
total. `security/poc/poc_privesc.py` walks the whole chain:

```
[1] POST /register  "is_admin": true      -> 201, is_admin=True
[2] POST /login                           -> 200, bearer token
[3] GET  /orders/                         -> every order, not just the attacker's
[4] GET  /orders/summary                  -> victim.customer@example.com, total 4207.55

IMPACT: an anonymous internet user read another customer's email address and
        order history in 4 HTTP requests.
VERDICT: VULNERABLE
```

**The fix.** `UserCreate` drops the field and sets `extra="forbid"`, so a body
carrying `is_admin` now returns 422. `create_user` hardcodes `is_admin=False`.
Admins are provisioned out of band with `scripts/create_admin.py`. Post-fix the
same PoC prints `VERDICT: BLOCKED` and exits 0.

## Notes on honesty

- **ECOM-05 (rate limiting)** is an in-process counter. It does not survive a
  restart and does not coordinate across replicas. Behind more than one instance
  the real control is a shared store (Redis) or an edge WAF. This raises the cost
  of guessing against a single instance; it is not a distributed limiter.
- **ECOM-07 (enumeration)** is reduced, not eliminated. The response for a taken
  account still differs from a successful signup by status code. Fully closing the
  oracle requires an email-confirmation flow.
- **ecdsa PYSEC-2026-1325** surfaced by pip-audit is triaged as not reachable
  (this service signs with HS256, not ECDSA) and recorded in
  `security/baseline.json` with an expiry, not silently ignored.
