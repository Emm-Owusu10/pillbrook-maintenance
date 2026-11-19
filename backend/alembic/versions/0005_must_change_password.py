"""Add the must-change-password flag and the temporary password's expiry to users.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("temporary_password_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        op.f("ck_users_temporary_password_needs_change"),
        "users",
        "temporary_password_expires_at IS NULL OR must_change_password",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_temporary_password_needs_change"), "users", type_="check")
    op.drop_column("users", "temporary_password_expires_at")
    op.drop_column("users", "must_change_password")