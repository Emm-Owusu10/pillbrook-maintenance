# Progress log

One entry per step: what was built, what was tested, what went wrong.

## Step 0: Requirements and planning (27 October)

- Reviewed the project document; agreed roles, workflow, lifecycle, and stack (see decisions D1 to D17).
- Revised Chapter Three: three roles, 29 functional, 8 non-functional and 15 security requirements,
  nine diagrams, permission matrix, and status lifecycle.
- Approved: all seven confirmation items, the stack table, and the performance targets.

## Step 1.1: Project skeleton (27 to 28 October)

**Built:** configuration loader that refuses weak or missing secrets; application factory; safe error
handling; restricted CORS; hidden API docs in production; `/health`; test setup; `.gitignore`.

**Files:** `app/config.py`, `app/main.py`, `tests/conftest.py`, `tests/test_config.py`, `tests/test_app.py`,
`pytest.ini`, `requirements.in`, `requirements-dev.in`, `requirements.lock.txt`, `.env.example`, `.gitignore`.

**Results:**
- 25 tests passed (16 configuration, 9 application), before and after the `httpx2` change.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues in 105 lines.
- `/health` returned 200; `/docs` returned 200 in development; an unknown route returned 404.
- Start without `.env`: stopped with `ConfigError: SECRET_KEY is not set`, no server running.

**Problems and fixes:**
- Nine tests errored with `fixture 'client' not found`. `conftest.py` was missing or misplaced.
  The cause was not recorded.
- A test-client warning led to replacing `httpx` with `httpx2` (D21).

## Step 1.2: Database foundation (29 October)

**Built:** PostgreSQL accounts and databases; SQLAlchemy base class with a constraint naming convention;
Alembic with a first migration that gives the app account read and write access to future tables only;
database settings validation; `check_db` command; database permission tests.

**Files:** `app/config.py` (replaced), `app/database.py`, `app/check_db.py`, `alembic.ini`,
`alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_baseline_privileges.py`,
`tests/conftest.py` (replaced), `tests/test_config.py` (replaced), `tests/test_database.py`,
`.env.example`, `requirements.in`.

**Results:**
- 43 tests passed (27 configuration, 9 application, 7 database).
- Migration: upgrade, downgrade, and upgrade again all ran cleanly. `heads` and `current` show `0001`.
- `check_db`: connected as `pillbrook_app` to PostgreSQL 18.2.
- Manual check: `CREATE TABLE` as `pillbrook_app` returned `permission denied for schema public`.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues in 272 lines.
- The `postgres` access rules were restored to `scram-sha-256` after the password reset.

**Problems and fixes:**
- Forgotten `postgres` password: reset by briefly setting `trust` in `pg_hba.conf` for local connections,
  setting a new password with `\password postgres`, then restoring `scram-sha-256` and restarting the service.
- SQL typed into PowerShell instead of psql: SQL belongs at the `postgres=#` prompt.
- `check_db.py` was not found: the file was missing or misnamed.
- The migration file sat in `alembic\` and `versions` had been created as a file. Alembic therefore saw no
  migration, and one test failed. Fixed by creating `versions` as a folder and moving the file in.
- My first downgrade test could pass with no migration at all. Replaced with a test that checks access
  exists while migrated and disappears after the downgrade, and added a test that the migration is registered.

## Unresolved

- Repository scan for committed secrets (SR10): no source control in use yet.
- `requirements.lock.txt` includes development tools. A production-only list comes in Phase 6.