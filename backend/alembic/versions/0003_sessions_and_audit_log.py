"""Create the sessions and audit_log tables.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import context, op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _app_role() -> str:
    quote = op.get_context().dialect.identifier_preparer.quote
    return quote(context.config.attributes["app_role"])


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.user_id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"])

    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("target", sa.String(length=254), nullable=True),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.user_id"], name=op.f("fk_audit_log_actor_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("log_id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_lookup"), "audit_log", ["event_type", "target", "created_at"])

    # The default privileges from migration 0001 let the application account change rows in every
    # new table. An audit log must not be editable, so take those rights away: it may only add
    # and read entries.
    op.execute(f"REVOKE UPDATE, DELETE ON audit_log FROM {_app_role()}")


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("audit_log")