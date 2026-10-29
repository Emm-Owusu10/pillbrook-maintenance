"""Baseline: give the application account data access to future tables, and nothing more.

Revision ID: 0001
Revises:
"""
from alembic import context, op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _app_role() -> str:
    # Quoting makes the account name safe to place inside a SQL statement.
    quote = op.get_context().dialect.identifier_preparer.quote
    return quote(context.config.attributes["app_role"])


def upgrade() -> None:
    role = _app_role()
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    # Every table the owner creates from now on gives the application read and write access to
    # its rows. Changing or dropping tables stays with the owner.
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
    )


def downgrade() -> None:
    role = _app_role()
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {role}"
    )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {role}")