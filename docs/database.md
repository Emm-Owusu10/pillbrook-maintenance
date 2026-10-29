# Database

Current state: no tables yet. The migration `0001` sets up access rules only.

## Accounts and databases

| Name | Purpose | Rights |
|---|---|---|
| `pillbrook_owner` | Runs migrations | Owns the databases; can create, alter and drop tables. Not a superuser. |
| `pillbrook_app` | The running application | Connect; read and write rows in tables the owner creates. Cannot create, alter, truncate or drop. Not a superuser. |
| `postgres` | One-time setup only | Superuser. Its password never goes in the project. The app refuses to use it. |

| Database | Use |
|---|---|
| `pillbrook` | Development data |
| `pillbrook_test` | Automated tests only. Tests undo migrations here, so names must end in `_test`. |

## Migrations

| Revision | What it does |
|---|---|
| `0001` | Removes the right to create objects in the `public` schema from everyone, lets the app account use the schema, and grants the app account SELECT, INSERT, UPDATE, DELETE on all tables the owner creates later. Downgrade reverses this. |

## Rules

- Change the database only through Alembic migrations. Never edit a migration that has been applied.
- Primary keys are UUIDs. Timestamps are timezone-aware.
- Allowed values (role, priority, status) are enforced with check constraints.
- Constraint names follow the convention in `app/database.py`.
- Every migration is tested up and down on `pillbrook_test`.

## Tables planned, by step

| Table | Step | Purpose |
|---|---|---|
| `users` | 2.1 | Accounts, role, password hash, verification time |
| `audit_log` | 2.2 | Security events |
| `farm_settings` | 2.5 | Farm access code, stored encrypted |
| `auth_tokens` | 2.5 | Hashed verification and reset tokens |
| `maintenance_requests` | 3.1 | Reported faults and their status |
| `attachments` | 3.2 | Photo references; at most two per request |
| `request_edits` | 3.3 | Edits made in the 15-minute window |
| `notifications` | 3.4 | In-app notifications |
| `maintenance_records` | 3.6 | Actions recorded by the Facility Manager |