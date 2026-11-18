# API reference (so far)

All addresses start with `/api`. Interactive documentation is at `/api/docs` in development only.

| Method | Address | Who | What it does |
|---|---|---|---|
| GET | `/api/health` | anyone | `{"status":"ok"}` |
| POST | `/api/auth/login` | anyone | Body `{"email", "password"}` (JSON only). On success returns the user, the role's `permissions` and a CSRF token, and sets the session cookie |
| GET | `/api/auth/me` | signed in | Returns the user, the role's `permissions` and the CSRF token |
| POST | `/api/auth/logout` | signed in | Needs the `X-CSRF-Token` header. Ends the session and clears the cookie. Harmless if nobody is signed in |
| POST | `/api/auth/register` | anyone | Body `{"name", "email", "password", "access_code"}`. Needs the farm access code. Creates a Farm User. Returns `verification_required` and `verification_email_sent` |
| POST | `/api/auth/verify-email` | anyone | Body `{"token"}`. Confirms an address once with the code from an email |
| POST | `/api/auth/resend-verification` | anyone | Body `{"email"}`. Always answers 202 with the same message |
| GET | `/api/auth/options` | anyone | `{"email_reset_available": true or false}` |
| POST | `/api/auth/change-password` | signed in | Body `{"current_password", "new_password"}` plus `X-CSRF-Token`. Works even on a temporary password. Returns 204 |
| POST | `/api/auth/forgot-password` | anyone | Body `{"email"}`. Always answers 202 with the same message |
| POST | `/api/auth/reset-password` | anyone | Body `{"token", "new_password"}` with the code from an emailed link. Returns 204 |
| POST | `/api/admin/users/reset-password` | `manage_users` | Body `{"email"}` plus `X-CSRF-Token`. Returns the name, email, a one-time `temporary_password` and `expires_at` (`Cache-Control: no-store`) |

## Answers to know

| Status | Meaning |
|---|---|
| 200, 204 | Worked |
| 401 | Wrong email or password (always the same message), or not signed in |
| 403 | A change was attempted without the matching `X-CSRF-Token` |
A 403 has two meanings. With the message "The request could not be verified" the `X-CSRF-Token` header was
missing or wrong. With "You do not have permission to do this." the person's role does not allow the
function; the attempt is recorded in the audit log. Someone else's data answers 404, never 403.
| 422 | The request body was malformed. The reply names the fields, never the values |
| 429 | Too many failed attempts for that email. Try again after the time in `Retry-After` (600 seconds) |
| 400 | The confirmation link is not valid or has expired (unknown, used and expired look alike) |
| 409 | An account with this email address already exists (only after the access code was correct) |
| 202 | Accepted: used by the resend endpoint whether or not an email was sent |
`403` on registration means the farm access code is wrong or registration is not open yet. `429` means
registration is paused after too many wrong codes; the `Retry-After` header says how long (600 seconds).
Errors in the details come back as `422` with a list of `{field, message}` entries.
Sign-in and `/api/auth/me` now include `must_change_password`. While it is true, every function except
`/api/auth/me`, change password and sign-out answers `403` with "You must choose a new password before you
continue." (a different message from the permission refusal). Wrong guesses at the current password on the change
page answer `403` and count towards the same lock, which then answers `429`.


## Sessions

- The cookie is `session` in development and `__Host-session` in production. It is HttpOnly and
  SameSite=Strict, and Secure in production.
- A session ends after 60 minutes without activity or 12 hours in total, or at once if the user is deactivated.
- Every request that changes data must send `X-CSRF-Token` with the value returned by login or `/api/auth/me`.