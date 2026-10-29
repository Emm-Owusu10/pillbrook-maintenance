# Pill Brook Facility Maintenance System

A web application for reporting and tracking facility maintenance at Pill Brook Aquatics Ltd.
Built with React, FastAPI, and PostgreSQL. This is a capstone project; the design is in Chapter Three.

Documentation: [requirements](docs/requirements-checklist.md) | [decisions](docs/decisions.md) |
[progress log](docs/progress-log.md) | [database](docs/database.md) | [roadmap](docs/roadmap.md)

## What you need (Windows, PowerShell)

- Python 3.12
- PostgreSQL 18 (examples use `C:\Program Files\PostgreSQL\18\bin\psql.exe`)
- Node.js 22 (needed from Step 1.3)

## Project layout

```
pillbrook-maintenance\
├── README.md
├── .gitignore
├── docs\                      project documentation
└── backend\
    ├── .env.example           settings template (copy to .env)
    ├── alembic.ini            migration tool settings
    ├── alembic\               database migrations (versions\ must be a folder)
    ├── app\                   the application (config, database, API)
    ├── tests\                 automated tests
    ├── pytest.ini
    ├── requirements.in        direct runtime dependencies
    ├── requirements-dev.in    adds test and security tools
    └── requirements.lock.txt  exact installed versions
```

## First-time setup

1. Create the environment and install, from `backend`:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip
   .\.venv\Scripts\python -m pip install -r requirements-dev.in
   .\.venv\Scripts\python -m pip freeze > requirements.lock.txt
   ```
2. Create the database accounts and databases. Open psql as the `postgres` superuser:
   ```powershell
   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost
   ```
   then, inside psql (the `\password` lines prompt for a password without showing it):
   ```sql
   CREATE ROLE pillbrook_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
   CREATE ROLE pillbrook_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
   \password pillbrook_owner
   \password pillbrook_app
   CREATE DATABASE pillbrook OWNER pillbrook_owner;
   CREATE DATABASE pillbrook_test OWNER pillbrook_owner;
   REVOKE ALL ON DATABASE pillbrook FROM PUBLIC;
   REVOKE ALL ON DATABASE pillbrook_test FROM PUBLIC;
   GRANT CONNECT ON DATABASE pillbrook TO pillbrook_app;
   GRANT CONNECT ON DATABASE pillbrook_test TO pillbrook_app;
   ```
3. Copy `.env.example` to `.env`. Fill in `SECRET_KEY` and the four database URLs.
   Generate each secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   (use `24` instead of `48` for database passwords).
4. Create the database structure: `python -m alembic upgrade head`
5. Check everything: `python -m pytest -q` and `python -m app.check_db`.

## Everyday commands (from `backend`, with the virtual environment active)

| Task | Command |
|---|---|
| Start the API | `python -m uvicorn app.main:create_app --factory --reload` |
| Run the tests | `python -m pytest -q` |
| Apply migrations | `python -m alembic upgrade head` |
| Show the current migration | `python -m alembic current` |
| Undo all migrations (test database only) | `python -m alembic downgrade base` |
| Check the database connection | `python -m app.check_db` |
| Dependency audit | `python -m pip_audit` |
| Code security scan | `python -m bandit -r app alembic` |

In development, API documentation is at http://127.0.0.1:8000/docs (it is hidden in production).

## Security rules

- Never commit `.env`. It holds the database passwords and the secret key.
- The running app uses `pillbrook_app`, which can read and write rows but cannot change tables.
  Only migrations use `pillbrook_owner`.
- The app refuses to start without a strong `SECRET_KEY`, or if its database URL uses `postgres`.
- Keep the `postgres` superuser password out of the project.
- Never run the tests against the real database. The tests refuse any database name not ending in `_test`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `psql` is not recognized | PostgreSQL's folder is not on PATH. Use the full path in quotes with `&`. |
| `CREATE : The term 'CREATE' is not recognized` | SQL was typed in PowerShell. Start psql first; SQL belongs at the `postgres=#` prompt. |
| `postgres-#` prompt keeps appearing | psql is waiting for a semicolon to end the statement. |
| `fixture 'client' not found` | `conftest.py` is missing, misnamed, or not in `tests\`. |
| `No module named app.check_db` | The file is missing or misnamed. Windows may hide a `.txt` extension. |
| `alembic upgrade` prints no "Running upgrade" | The migration must be inside `alembic\versions\`, and `versions` must be a folder, not a file. |
| `password authentication failed for user "postgres"` | Wrong superuser password. Reset steps are in `docs/progress-log.md`, Step 1.2. |
| `Could not connect` from `check_db` | The passwords in `.env` do not match those set in psql. Reset with `\password`. |