# Requirements and security checklist

Status as of the end of Step 1.3 (30 October 2026). Source: Chapter Three, revised version.
"Verified" means a test or manual check passed and the result was recorded in the progress log.

## Functional requirements (all not started, by design)

| ID | Requirement (short) | Planned step | Status |
|---|---|---|---|
| FR1 | Register with name, email, password, farm access code | 2.5 | Not started |
| FR2 | Email verification link before login | 2.5 | Not started |
| FR3 | New accounts get the Farm User role | 2.5 | Not started |
| FR4 | Login by email and password; limit failed attempts | 2.2 | Not started |
| FR5 | Restrict every function by role | 2.3 | Not started |
| FR6 | Logout and idle session expiry | 2.2 | Not started |
| FR7 | Password reset by emailed link | 2.6 | Not started |
| FR8 | Administrator-assisted password reset | 2.6 | Not started |
| FR9 | Administrator manages users and roles | 2.7 | Not started |
| FR10 | Administrator changes access code; Facility Manager views it | 2.7 | Not started |
| FR11 | Submit request with up to two photos | 3.1, 3.2 | Not started |
| FR12 | Reject invalid input and name each problem | 3.1 | Not started (the error format that names each field is in place and tested) |
| FR13 | Photo rules: type, size, metadata removal, private storage | 3.2 | Not started |
| FR14 | Store request with reporter, time, status Open | 3.1 | Not started |
| FR15 | Reporter edits within 15 minutes, before action | 3.3 | Not started |
| FR16 | Reporter views own requests, status, photos | 3.3 | Not started |
| FR17 | Dashboard with filters for Administrator and Facility Manager | 3.5 | Not started |
| FR18 | Keyword search within permitted requests | 3.5 | Not started |
| FR19 | Facility Manager sets In Progress | 3.6 | Not started |
| FR20 | Facility Manager records action and remarks | 3.6 | Not started |
| FR21 | Facility Manager marks Fixed | 3.7 | Not started |
| FR22 | Reporter confirms or reopens | 3.7 | Not started |
| FR23 | Close a Fixed request after N days without reply | 3.8 | Not started |
| FR24 | Notify Administrators and Facility Managers of new requests | 3.4 | Not started |
| FR25 | Notify reporter when marked Fixed | 3.7 | Not started |
| FR26 | Notify managers when reporter confirms or reopens | 3.7 | Not started |
| FR27 | Notification list, unread count, mark as read | 3.4 | Not started |
| FR28 | Summary figures: per status, per location, average time to fix | 4.1 | Not started |
| FR29 | Record security events; Administrator views them | 2.2 (record), 4.2 (view) | Not started |

## Non-functional requirements

| ID | Requirement (short) | Planned step | Status |
|---|---|---|---|
| NFR1 | Usability: first report in under X minutes on a phone | Phase 5 | Groundwork: mobile-first layout, 44 px tap targets, visible focus outlines |
| NFR2 | Pages respond within 3 s for at least 50 concurrent users | Phase 5 | Not started |
| NFR3 | Saved data survives restart; failed notification does not lose a request | 3.4, Phase 5 | Not started |
| NFR4 | Availability target (paid, always-on deployment only) | Phase 6 | Not started |
| NFR5 | 100 users, at least 50 concurrent, 5,000 requests with photos | Phase 5 | Not started |
| NFR6 | Separate layers, migrations, a test for every requirement | Every step | In progress: layers, migrations and tests exist (44 backend, 15 frontend) |
| NFR7 | Database enforces keys, allowed values, two-photo limit | With each table | Partly verified: the users table refuses duplicate emails, unknown roles and uppercase emails |
| NFR8 | Configuration from environment; backup and export procedure | Phase 5, 6 | Partly: environment configuration and migrations verified; backup procedure pending |

## Security requirements (ASVS 5.0; target level to be confirmed)

| ID | Requirement (short) | Planned step | Status | Evidence |
|---|---|---|---|---|
| SR1 | Argon2id password hashing, never logged | 2.1 | Verified for storage; login in 2.2 | Hash uses argon2id with the agreed settings, a salt per hash, and never contains the password; no message repeats it |
| SR2 | Password policy per NIST SP 800-63B-4 | 2.1 | **Verified** | 13 rule tests; list of 99,840 common passwords; lengths 15 to 128, NFKC |
| SR3 | Login throttling; same message for unknown email and wrong password | 2.2 | Not started | |
| SR4 | Secure session cookie, CSRF protection | 1.3, 2.2 | Groundwork done | One origin in development (proxy); the API helper sends same-origin credentials and has a place for the CSRF header. Cookie and CSRF arrive in Step 2.2. |
| SR5 | Role and ownership checks; deny by default | 2.3 onward | Not started | |
| SR6 | Validation, parameterised queries, safe output | 2.1 onward | Partly verified | SQLAlchemy used for all database access so far; email format check; React escapes text |
| SR7 | Photo upload checks and private storage | 3.2 | Not started | |
| SR8 | Access code, verified email, rate limits on registration and reset | 2.5, 2.6 | Not started | |
| SR9 | Single-use, time-limited, hashed tokens | 2.5, 2.6 | Not started | |
| SR10 | Secrets from environment; refuse to start without them | 1.1, 1.2 | **Verified** | 27 configuration tests; start-without-secret check; staged files scanned for passwords before the first commit |
| SR11 | Generic errors; log events without secrets | 1.1, 2.2 | Partly verified | Generic errors tested; audit log pending |
| SR12 | HTTPS, security headers, restricted CORS | 1.1, Phase 5, 6 | Partly verified | CORS and hidden docs tested; HTTPS and headers pending |
| SR13 | Application account cannot change the schema | 1.2 | **Verified** | 7 database tests; manual psql check |
| SR14 | Pinned and audited dependencies at every step | Every step | **Verified through Step 1.3** | pip-audit clean (Step 1.2); npm audit: 0 vulnerabilities; package-lock.json and requirements.lock.txt record exact versions |
| SR15 | Data minimisation and retention period | 3.x, Phase 5 | Not started | |