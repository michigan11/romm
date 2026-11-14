"""Add user feedback notes, including game requests.

Revision ID: 0155_feedback
Revises: 0154_announcement
Create Date: 2026-11-14 00:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

from models.feedback import (
    FEEDBACK_APP_VERSION_MAX_LENGTH,
    FEEDBACK_GAME_TITLE_MAX_LENGTH,
    FEEDBACK_KIND_MAX_LENGTH,
    FEEDBACK_PAGE_PATH_MAX_LENGTH,
    FEEDBACK_USERNAME_MAX_LENGTH,
)

revision = "0155_feedback"
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
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "username",
            sa.String(length=FEEDBACK_USERNAME_MAX_LENGTH),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=FEEDBACK_KIND_MAX_LENGTH), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "page_path",
            sa.String(length=FEEDBACK_PAGE_PATH_MAX_LENGTH),
            nullable=False,
        ),
        sa.Column(
            "app_version",
            sa.String(length=FEEDBACK_APP_VERSION_MAX_LENGTH),
            nullable=False,
        ),
        sa.Column("platform_id", sa.Integer(), nullable=True),
        sa.Column(
            "game_title",
            sa.String(length=FEEDBACK_GAME_TITLE_MAX_LENGTH),
            nullable=True,
        ),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"], if_not_exists=True)
    op.create_index(
        "ix_feedback_platform_id", "feedback", ["platform_id"], if_not_exists=True
    )
    op.create_index(
        "ix_feedback_created_at", "feedback", ["created_at"], if_not_exists=True
    )
    op.create_index("ix_feedback_kind", "feedback", ["kind"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("feedback", if_exists=True)
