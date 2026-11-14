"""Add the server-wide announcement, disabled, and per-user dismissals.

Revision ID: 0162_announcement
Revises: 0161_save_channels
Create Date: 2026-11-14 00:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

from utils.database import is_postgresql

revision = "0162_announcement"
down_revision = "0161_save_channels"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column[datetime]]:
    return [
        sa.Column(
            column,
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        )
        for column in ("created_at", "updated_at")
    ]


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_table(
        "announcement_dismissals",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        if_not_exists=True,
    )
    _seed_announcement()


def _seed_announcement() -> None:
    """Insert the disabled singleton when a partial run left the table empty."""
    bind = op.get_bind()
    statement = (
        "INSERT INTO announcements "
        "(id, enabled, title, message, revision, created_at, updated_at) "
        "VALUES (1, false, '', '', 0, now(), now()) ON CONFLICT (id) DO NOTHING"
        if is_postgresql(bind)
        else "INSERT IGNORE INTO announcements "
        "(id, enabled, title, message, revision, created_at, updated_at) "
        "VALUES (1, false, '', '', 0, now(), now())"
    )
    bind.execute(sa.text(statement))


def downgrade() -> None:
    op.drop_table("announcement_dismissals", if_exists=True)
    op.drop_table("announcements", if_exists=True)
