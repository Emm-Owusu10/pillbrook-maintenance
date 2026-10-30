# Roadmap (draft for approval)

Each step ends with tests and your confirmation. From Step 2.2 onward, every step has two parts:
the API, then the screens, each confirmed separately. Nothing is cut or reordered without approval.

| Step | Content | Requirements |
|---|---|---|
| 1.1 | Project skeleton, configuration, safe errors | Done |
| 1.2 | PostgreSQL accounts, migrations | Done |
| 1.3 | React skeleton and API connection | Done |
| 2.1 | Users table, Argon2id hashing, password policy, first Administrator | SR1, SR2 |
| 2.2 | Login, sessions, logout, idle expiry, throttling, audit log | FR4, FR6, FR29, SR3, SR4 |
| 2.3 | Role-based access control | FR5, SR5 |
| 2.4 | Email sending (log mode in development; provider interface) | Supports FR2, FR7 |
| 2.5 | Farm access code, registration, email verification | FR1, FR2, FR3, SR8, SR9 |
| 2.6 | Password reset and administrator-assisted reset | FR7, FR8 |
| 2.7 | User management and access code management | FR9, FR10 |
| 3.1 | Submit, validate, store requests | FR11, FR12, FR14 |
| 3.2 | Photos: validation, metadata removal, private storage | FR13, SR7 |
| 3.3 | Own requests, edit window | FR15, FR16 |
| 3.4 | In-app notifications for new requests | FR24, FR27 |
| 3.5 | Dashboard with filters; search | FR17, FR18 |
| 3.6 | In Progress and action records | FR19, FR20 |
| 3.7 | Fixed, confirm or reopen, related notifications | FR21, FR22, FR25, FR26 |
| 3.8 | Close unanswered requests | FR23 |
| 4.1 | Summary figures | FR28 |
| 4.2 | Audit log viewer | FR29 |
| 5 | Hardening and non-functional testing: security review, load, usability, backup and restore | NFR1 to NFR8, SR11 to SR15 |
| 6 | Deployment to Render, production dependency list, handover | NFR4, SR12 |