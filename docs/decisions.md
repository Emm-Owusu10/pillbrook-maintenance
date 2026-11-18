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
| D15 | One Render web service serves the API and the built React files from one origin, with a secure session cookie. | Avoids cross-site cookie problems. |
| D16 | Photo storage and hosting plan: provider to be chosen. The email service is decided in D61 (Resend, when email is turned on). | Updated 17 November. See D22 and D61. |
| D17 | Development on Windows without Docker, using PostgreSQL 18.2 installed directly. | Docker is not installed. Render offers PostgreSQL 18. |
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
| D49 | A function the person's role does not allow answers 403. Someone else's data (for example another person's request) will answer 404, so nobody can learn that it exists. | Refusing and hiding are different needs. |
| D50 | Every refused attempt is recorded in the audit log (`access_denied`, with the permission name and the address). The reply never names the permission. | Repeated refusals can reveal probing. |
| D51 | The permission table is `app/permissions.py`: 13 permissions, three roles, read-only at run time. A role the table does not know gets nothing. The role is read from the database on every request. | One place to read, check and change the rules; changes apply at once. |
| D52 | The server sends the role's permissions at sign-in and in `/api/auth/me`. The screens only hide links and show "You don't have permission"; the server enforces everything. | The rules live in one place, and hiding a link is not security. |
| D53 | A test advertises every route through the application's own description and requires that each one not on the open list answers a signed-out visitor with 401. | A function added without a guard fails the build. It cannot catch a guard with the wrong permission. |
| D54 | Exactly three routes are open: `GET /api/health`, `POST /api/auth/login`, `POST /api/auth/logout`. A test counts them. | Opening a route must be a deliberate, reviewed decision. |
| D55 | Never mark a route `include_in_schema=False` (it would hide it from D53). Every new endpoint gets a role-by-role test and its permission is listed against Table 3.3. | Closes the gap D53 leaves. |
| D56 | Real email sending is postponed to a later enhancement. We build the secure design now (mailer, outbox, verification and reset flows) and add the provider later. | The domain records, account and quota need Pill Brook's involvement; the flows can be built and tested without them. |
| D57 | Two mail modes: `off` (nothing sent) and `outbox` (development only: each email saved as a file in `backend/outbox`). Production refuses `outbox`; `provider` is rejected until it exists. | A flow can be tested end to end without sending anything. |
| D58 | Until email is on, production accounts will not have verified email addresses, and the address serves as the login name only. Forgotten passwords are handled by the Administrator (one-time temporary password, shown once, which the person must change at first sign-in). A server command recovers the Administrator's own account. | Accepted by the developer on 8 November. A farm where everyone knows each other can use a person-to-person check. |
| D59 | `REQUIRE_EMAIL_VERIFICATION` (default false) can only be true while email is on. Turning it on later makes unverified users confirm their address; no data change is needed. | One switch controls the whole feature. |
| D60 | Messages are checked before anything is written: no line breaks in recipient or subject, a valid address, size limits. File names hold time and random characters, never the address. `backend/outbox/` is ignored by Git. Errors and logs never repeat a message's content. | Stops header injection; outbox files can hold live one-time links. |
| D61 | When email is turned on, the planned provider is Resend with a verified sending subdomain of `pbafish.com` (for example `notify.pbafish.com`), a sending-only API key limited to that domain, a daily cap below the free plan's 100, and a call made with Python's built-in tools. | Researched on 8 November. Re-check Resend's current limits before using it. |
| D62 | The farm access code is stored encrypted (Fernet, with a key derived from SECRET_KEY by HKDF). If SECRET_KEY changes, the stored code can no longer be read and registration stays closed until the Administrator sets a new one. | A copy of the database does not reveal the code, and the Facility Manager can still be shown it (FR10). Keep SECRET_KEY stable. |
| D63 | Registration checks, in order: the pause, the access code, the details (name, email, password), and only then whether the address exists. | A visitor without the code learns nothing, not even which addresses are registered. |
| D64 | Ten wrong codes in ten minutes pause registration for the whole farm for ten minutes. Sign-in is unaffected. | Stops guessing before a trusted visitor address exists. A mischievous visitor could pause registration; limits per visitor follow in Phase 5. |
| D65 | One-time links last 24 hours, work once, and only a SHA-256 fingerprint is stored. The code sits after a `#` in the link, which browsers never send to servers, so it stays out of server logs. A single database statement checks and uses a token, so two requests cannot both use it. A new link cancels older unused ones. | SR9. |
| D66 | A person may ask for 3 confirmation emails per address per hour. The reply is always the same, whether or not the address exists, and the email is sent after the reply. | Prevents finding out which addresses are registered, by words or by speed. |
| D67 | While `REQUIRE_EMAIL_VERIFICATION` is false, unverified accounts can sign in and `email_verified_at` stays empty (it is never falsely filled). | D58. The same switch turns confirmation on later without changing data. |
| D68 | The open routes are now six: health, login, logout, register, verify-email, resend-verification. A test counts them. | Each is public by nature; adding one stays a deliberate decision (D54). |
| D69 | `cryptography` was added (approved). `pip-audit` found advisories in `dnspython` and `opentelemetry-api` (installed through other packages) on 13 November; both were upgraded. | SR14. Audits are re-run at every step. |
| D70 | Bandit finding B105 on the label `RESET_PASSWORD` is a reviewed false positive, suppressed on that line only with the reason beside it. | The label names a kind of link, not a password. |
| D71 | `PUBLIC_BASE_URL` (default `http://127.0.0.1:5173`) is the address placed at the start of links in emails. It must be exact, with no trailing slash, and https in production when verification is required. | A link must never be built from the request, which an attacker could influence. |
| D72 | Brand colours come from the Pill Brook logo: navy `#141444` and orange `#EC6C3C`, plus a brighter blue `#1F4FBF`. They are variables at the top of `styles.css`. The logo's accent is orange, so the accent is orange; a yellow is one line (`--accent`). | One place to change the look; measured from the supplied logo on 17 November. |
| D73 | Button text on the orange accent is navy (5.6:1 contrast); white on that orange fails (3.1:1). Every text and background pairing in the palette was checked against 4.5:1. | NFR1 and accessibility. |
| D74 | The header is navy with white links on every page. The signed-out landing page is a full-width hero (headline, two buttons, artwork, a wave into white) followed by a three-step "How it works". Other pages keep the simple 40 rem layout. | Matches the reference system's structure. The artwork is an original drawing of the logo's sun and fish, to be replaced by official artwork. |
| D75 | A confirmation link opens a page, and the page sends the code. Opening the link does not confirm the address by itself. | Email security tools open every link to scan it; a link that confirmed on opening could be triggered by a scanner. |
| D76 | The page reads the code from the part of the link after `#`, replaces the address at once so the code is not left in the address bar or the history, never stores it, and sends it once even when React runs its effect twice. | The code is a secret for 24 hours. |
| D77 | On the Register page the passwords are typed twice and are emptied only when the server refused the password; the access code is shown as typed and capitalised; the rules appear above the password box. | A mistyped code should not make someone retype two long passwords; masking a 12-character code on a phone causes mistakes. |
| D78 | After registering, the person goes to the sign-in page with "Account created. You can now sign in." (no automatic sign-in); when verification is on, a "Check your email" page with a resend form appears instead. | Simpler and safer: a session starts only through a real sign-in. |
| D79 | A temporary password is 16 lowercase letters and digits, leaving out i, l, o, 0 and 1 (about 79 bits), shown in groups of four with dashes. It may be typed with or without the dashes and spaces and in any case. It stays valid for 24 hours or until the person replaces it, and the Administrator sees it once; the reply is marked "do not store" and the audit log never holds it. | Easy to read out and to type; strong enough to guess-proof. |
| D80 | A person on a temporary password may only check who they are, change the password and sign out. This is enforced in the guard every protected function uses, so no later function can forget it. The reply is a 403 with its own message, so the screens can send the person to the change page. | The rule belongs in one place. |
| D81 | A reset ends every sign-in the person has and cancels reset links already emailed. The Administrator cannot reset their own account (they use Change password); a deactivated account is refused; the server command can reset any account, including the Administrator's. | A reset must cut off whoever held the old password, and the Administrator must never be locked out for good. |
| D82 | Change password needs the current password. Wrong guesses count towards the same lock as sign-in (4 in 10 minutes). Success ends the other sign-ins but keeps the browser that made the change. The new password must pass the password rules and differ from the current one. | A stolen session must not be able to guess the current password. |
| D83 | Reset by emailed link: 1 hour, single use, with the code after a `#`; built and tested, off until email is on. The password is checked before the link is used up, so a typing mistake does not waste it. "Forgot password" always answers the same, allows 3 emails per address per hour and sends after replying. | D66 and D65 applied to resets. |
| D84 | `GET /api/auth/options` tells the screens whether reset by email is possible and nothing else. The open routes are now nine. | The "Forgot password?" page shows only the instruction that works today. |
| D85 | `python -m app.reset_password` gives any account a temporary password from the server. It needs the server's own `.env`, and it is recorded in the audit log without the password. | Recovery for the Administrator when no one can sign in. |
| D86 | Audit event names in the code avoid the word "password" so bandit's B105 does not flag them as hardcoded passwords. The values stored in the log are unchanged (for example `password_changed`). | Keeps the scan meaningful. |


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
| Chapter Three changes: the 13 permission names, the 403 versus 404 policy, the `access_denied` audit event, and the weaker "no unguarded route" guarantee | Before the chapter is submitted |
| Who manages the DNS for `pbafish.com`; whether the domain already carries company email; the sender address Pill Brook accepts | When email is turned on |
| Chapter Three changes for email: FR2 and FR7 are enabled by a setting and the prototype runs with email off; FR8 moves from Should to Must; a Visitor cannot "verify email" or "reset password" until then; the diagrams and permission wording change a little | Before the chapter is submitted |
| Set the real farm access code on the production server and tell the Facility Manager | Step 6 (deployment) |
| Chapter Three changes: registration limits (10 wrong codes in 10 minutes), the encrypted access code, one-time link details (24 hours, single use, fingerprint only), the three new open routes, and `value_encrypted` in the Farm_Setting entity | Before the chapter is submitted |
| Official Pill Brook logo and artwork (SVG or transparent PNG) to replace the stand-in drawing; confirm the accent (orange as in the logo, or yellow) with the company | Before Chapter Four screenshots are final |
| Chapter Three changes: the Register screen fields, the "Check your email" and "Confirm your email" screens, and the rule that a link opens a page that sends the code | Before the chapter is submitted |
| Chapter Four screenshots still to take: Register page (empty, with rules), a refused password, a wrong access code, Check your email, the outbox email, the confirmed page, and the expired-link page | Before the chapter is submitted |
| Chapter Three changes: FR8 (Administrator-assisted reset) moves from Should to Must; the temporary password, the forced-change state and its rule; change password with the sign-in lock; reset by emailed link and its limits; the `options` route (nine open routes); two new attributes on User (`must_change_password`, `temporary_password_expires_at`); the new audit events | Before the chapter is submitted |
| If the temporary password for the account `pink@gmail.com` is a real person's, reset it with `python -m app.reset_password` (it was shown in a chat on 18 November) | Now |