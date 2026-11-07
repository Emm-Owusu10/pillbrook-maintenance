# API reference (so far)

All addresses start with `/api`. Interactive documentation is at `/api/docs` in development only.

| Method | Address | Who | What it does |
|---|---|---|---|
| GET | `/api/health` | anyone | `{"status":"ok"}` |
| POST | `/api/auth/login` | anyone | Body `{"email", "password"}` (JSON only). On success returns the user, the role's `permissions` and a CSRF token, and sets the session cookie |
| GET | `/api/auth/me` | signed in | Returns the user, the role's `permissions` and the CSRF token |
| POST | `/api/auth/logout` | signed in | Needs the `X-CSRF-Token` header. Ends the session and clears the cookie. Harmless if nobody is signed in |

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

## Sessions

- The cookie is `session` in development and `__Host-session` in production. It is HttpOnly and
  SameSite=Strict, and Secure in production.
- A session ends after 60 minutes without activity or 12 hours in total, or at once if the user is deactivated.
- Every request that changes data must send `X-CSRF-Token` with the value returned by login or `/api/auth/me`.