# Seed failure diagnostics — 18/10/2026

User's Vercel build140d7a8 now receives both required env variables and downloads verified models, then fails inside seed_demo's combined ValidationError/AccountError/IntegrityError handler. Prior output did not identify which case occurred; the remote root cause is not established merely by this generic failure.

Changed seed validation to precheck the configured password against all23 fixed demo usernames, before account creation. Build performs the same check before model download/migrations. Password errors expose only trusted validator codes/fixed usernames; data validation, service rejection and DB constraint errors are reported separately. Raw ValidationError messages and secret values are not printed. Transaction rollback, username collisions and previous-template preservation remain enforced.

Three regressions observed RED→GREEN: explicit weak-password reason/no records, all23 usernames checked, data error not mislabeled as password failure. Root seed+Vercel test run:17 passed in38.176s. Independent review: no critical/important findings; reviewer reran11 seed/build tests successfully.

Actual full build with the existing private `.env.vercel` values completed successfully, including all23 account password checks, verified models, migrations, seed, current-day rosters and collectstatic. Captured stdout/stderr checked against both private values: neither appeared. No user demo DB changed and no deployment created. User must use a new main deployment and inspect fresh diagnostics; this evidence does not claim a successful Vercel build.
