# Decision log

Every decision that shaped the system, with the reason. Dates are 2026.

## Requirements and workflow (27 October, approved)

| ID | Decision | Reason |
|---|---|---|
| D1 | Three roles: Farm User, Facility Manager, Administrator. One role per account. Anyone, whatever the role, can report a fault. Repair workers do not use the system. | Matches how the farm works. The Facility Manager records repair work. |
| D2 | Registration uses a farm access code and email verification, with rate limits. New accounts start as Farm User. | Open registration invites fake accounts; admin approval slows urgent reports. |
| D3 | Login by email. Password reset by single-use, time-limited emailed link. Administrator-assisted reset as a fallback. | All farm workers are expected to have email. |
| D4 | Request lifecycle: Open, In Progress, Fixed, Completed, Closed. The Facility Manager marks Fixed; only the reporter completes, or reopens with a reason. The Facility Manager or Administrator can close an unanswered Fixed request after N days. | A repair counts as finished when the reporter agrees. |
| D5 | Only the Facility Manager starts action, records action, and marks Fixed. The Administrator does not. | Least privilege. |
| D6 | Up to two photos per request, JPEG, PNG or WebP, 10 MB each. Seen by the reporter, Facility Manager and Administrator. GPS metadata removed. | Evidence without leaking location. |
| D7 | The reporter can edit for 15 minutes after submitting, and only while no action has started. Every edit is recorded. | Allows corrections without rewriting history. |
| D8 | In-app notifications for now: new request to Administrators and Facility Managers; Fixed to the reporter; confirm or reopen to managers. Email notifications later. | Email delivery is restricted on Render's free tier. |
| D9 | Reports: dashboard list with filters, plus summary figures. Exports later. | Levels A and B of the three options offered. |
| D10 | Targets: 3-second response, at least 50 concurrent users, 100 registered users, 5,000 requests with photos. | Design assumptions; the number of users is unknown. |
| D11 | Tables are created step by step, each in the step that first uses it. | Small, testable migrations. |
| D12 | Passwords follow NIST SP 800-63B-4: at least 15 characters, accept at least 64, no composition rules, reject common or breached passwords. | Current guidance. The NIST document was finalised in 2025. |

## Technology (27 October, approved)

| ID | Decision | Reason |
|---|---|---|
| D13 | React, FastAPI, PostgreSQL. | Specified in the project document. |
| D14 | SQLAlchemy 2 with Alembic, psycopg 3, Argon2id, Vite with React Router, Pillow, pytest, pip-audit, bandit. | Parameterised queries, versioned schema, current password hashing, minimal frontend tooling, tested and scanned code. |
| ID | Decision | Reason |
|---|---|---|
| D18 | A small built-in `.env` reader instead of a library. | One fewer dependency. |
| D19 | `ENVIRONMENT` defaults to production. API docs exist only in development. | A forgotten setting must not enable developer features. |
| D20 | Validation errors name the field and problem but never echo the submitted value. | The default response would echo a mistyped password. |
| D21 | Tests use `httpx2` instead of `httpx` (approved 28 October). | Starlette's test client now prefers `httpx2` and warns about `httpx`. |
| D22 | Two database accounts: an owner for migrations and a limited account for the app. The app refuses the `postgres` superuser and does not keep the owner's URL in memory. Migration 0001 gives the app account read and write access to future tables only. | Least privilege (SR13). |
| D23 | The database check is a command (`python -m app.check_db`), not a web page. | A public database status page would help attackers. |
| D24 | Tests run migrations only on databases whose names end in `_test`. | Prevents tests from touching real data. |

| D25 | All API addresses start with `/api` (health check is `/api/health`; docs `/api/docs`, development only). | Screen addresses and API addresses can never collide when the built app is served from one origin. |
| D26 | Frontend code is JavaScript, not TypeScript. | Chosen by the developer; fewer concepts to learn. TypeScript can be adopted later. |
| D27 | Frontend packages: react, react-dom, react-router (version 7 needs only this one package); dev tools vite, @vitejs/plugin-react, vitest, jsdom, @testing-library/react, @testing-library/dom. ESLint and jest-dom were left out. | Smallest set that meets the approved stack; fewer packages means a smaller supply-chain surface. ESLint can be reconsidered in Phase 5. |
| D28 | In development the browser talks only to the Vite server on 127.0.0.1:5173, which forwards `/api` to the backend on port 8000. The dev server is not reachable from other computers. | One origin, so CORS stays unused (D15); nothing exposed on the network. |
| D29 | Tools are always started with `python -m` (for example `python -m uvicorn`). | Windows Application Control blocks the `.exe` launchers in the virtual environment. |
| D30 | Common passwords are rejected using a list kept in the project: SecLists NCSC top 100,000 (MIT licence), compared case-insensitively, and also with trailing digits and symbols removed. If the list is missing, the check stops with an error instead of being skipped. | Works offline and sends nothing out; failing closed means a missing file cannot quietly weaken the rules. |
| D31 | Argon2id at the OWASP minimum: 19,456 KiB, 2 rounds, 1 lane. Measured at about 40 ms on the development computer. Re-measure on Render. Older hashes upgrade at the next login. | The free Render plan has little processing power. |
| D32 | Name parts and the email name (4 or more letters) and "pillbrook" must not appear in a password. | NIST asks for context-specific words to be rejected; the 4-letter limit avoids rejecting harmless passwords. |
| D33 | Email addresses are checked with `email-validator` without internet lookups, stored in lowercase, and the database refuses anything else. | Same result online or offline; one canonical form per address. |
| D34 | The first Administrator is created with `python -m app.create_admin`, which refuses to run if one exists. The email counts as verified. Further Administrators come from user management (Step 2.7). | The website must never offer a way to become an Administrator. |
| D35 | User IDs are generated by the database. The application account gets access to the users table through the default privileges from migration 0001, with no table-specific grant. | Confirms the Step 1.2 design works for a real table. |
| D36 | Sessions are kept in the database (table `sessions`): the cookie holds a random 256-bit code and the table holds only its SHA-256 fingerprint. A new login replaces any old session, and expired sessions are cleared at login. | A deactivated user can be signed out at once, and a leaked database holds no usable session codes. The Chapter Three ERD had no sessions entity. |
| D37 | A session ends after 60 minutes without activity or 12 hours in total. Activity is recorded at most once a minute. | Chosen for farm staff on phones: long enough not to interrupt work, short enough to limit a lost device. |
| D38 | Four wrong passwords for one email within 10 minutes lock login for that email for 10 minutes. Locked attempts are refused with 429 and a Retry-After header, are not logged, and do not extend the lock. Unknown and invalid emails are counted the same way. | Slows guessing without revealing which emails exist. A known address can be locked by someone else for 10 minutes; limits per computer address are planned for Phase 5. |
| D39 | The session cookie is HttpOnly, SameSite=Strict, Path=/, with Secure and the `__Host-` prefix in production only. Every request that changes data must carry an `X-CSRF-Token` header. | Two independent protections against cross-site request forgery. Browsers refuse Secure cookies on plain http, so development uses a plain `session` cookie. |
| D40 | The CSRF token is derived from the session code and SECRET_KEY, so nothing extra is stored. Changing SECRET_KEY invalidates every token; the screens fetch a new one from `/api/auth/me`. | Simple, and it gives SECRET_KEY a real job. |
| D41 | Every failed login returns the same message and status, and a placeholder password is checked when the email is unknown so timing is similar. Text typed in the email box is stored only when it is a valid email address. | Prevents discovering which accounts exist; people sometimes type a password into the email box. |
| D42 | The audit log (table `audit_log`) records login success, failure, lock, logout and session expiry. The application account may add and read entries but not change or delete them; removing old entries (retention) must be done with the owner account. An `ip_address` column exists but stays empty until Render's proxy handling is understood (Step 6). | A tamper-resistant record: someone who steals the application account cannot rewrite history. |
| D43 | The sign-in state and the CSRF token live in memory only. Nothing is written to local or session storage; a reload asks the server who is signed in. | A script on the page cannot find a stored secret, and the server stays the only authority. |
| D44 | After sign-in the app goes to the page the visitor asked for, otherwise the home page. Only a path starting with a single `/` is accepted. | A crafted sign-in link can never send someone to another website. |
| D45 | The sign-in form has a "Show password" box, autocomplete hints for password managers, 44 px controls, and empties and hides the password after a failed attempt. | Typing a 15-character password on a phone causes mistakes, and mistakes count toward the lock. |
| D46 | The System status page stays open to signed-out visitors. | It shows only whether the server is up and helps staff tell a connection problem from a server problem. A detailed Administrator-only page may follow in Phase 5. |
| D47 | Signing out on purpose returns to the public home page; a session that ends by itself returns to the sign-in page with "Your session has ended." | Each case needs a different next step. |
| D48 | If signing out fails because the connection is lost, the person stays signed in and is told so. | Otherwise they could believe they had signed out while the server still held their session. |

## Render free tier (checked 27 to 28 October; re-check before deployment)

- Web services sleep after about 15 minutes idle and take about a minute to wake.
- Uploaded files do not persist, so photos need separate storage (D16).
- Outbound SMTP ports are blocked on free web services, so email must use an HTTPS email service.
- The free database reportedly expires after 30 days. Sources disagree on any grace period, so assume none. There are no backups, so a backup and export procedure is required (NFR8).
- Render supports PostgreSQL 17 (default) and 18.
- The free tier is for the thesis prototype only. Real adoption needs a paid, always-on plan.

## Open items

| Item | Needed by |
|---|---|
| N days before auto-close (FR23) | Step 3.8 |
| Idle session timeout in minutes (FR6) | Step 2.2 |
| Data retention period (SR15) | Phase 5 |
| Usability target X minutes (NFR1); availability target (NFR4) | Phase 5, 6 |
| ASVS target level, 1 or 2 | Phase 5 |
| Object storage provider; email provider | Steps 2.4 and 3.2 |
| Whether Section 3.3 evidence (interviews or observation) has been gathered | Before the thesis chapter is submitted |
| Limits per computer address on login and registration; trusted proxy setting for the real visitor address | Phase 5 and Step 6 |
| Audit log retention period and how old entries are removed (owner account) | Phase 5 |
| Chapter Three changes: Sessions entity in the supporting ERD; FR4 limits (4 in 10 minutes, 10-minute lock); FR6 limits (60 minutes idle, 12 hours absolute); audit log columns and its append-only rule | Before the chapter is submitted |
| Chapter Three changes: login and sign-out behaviour, the "My account" page, the sign-in screen's show-password box | Before the chapter is submitted |
| Keep a private copy of `backend/.env` (for example in a password manager). It is not in Git, so a damaged file cannot be restored from the repository | Now |