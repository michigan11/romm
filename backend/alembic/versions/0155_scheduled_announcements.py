"""Add scheduled announcements.

Revision ID: 0155_scheduled_announcements
Revises: 0154_announcement
Create Date: 2026-11-14 00:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0155_scheduled_announcements"
down_revision = "0154_announcement"
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
        "scheduled_announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ends_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("activated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("activated_revision", sa.Integer(), nullable=True),
        sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("scheduled_announcements", if_exists=True)
