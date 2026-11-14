from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Final

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.platform import Platform


class FeedbackKind(enum.StrEnum):
    BUG = "bug"
    IDEA = "idea"
    OTHER = "other"
    REQUEST = "request"


FEEDBACK_KIND_MAX_LENGTH: Final = 16
FEEDBACK_MESSAGE_MAX_LENGTH: Final = 2000
FEEDBACK_PAGE_PATH_MAX_LENGTH: Final = 1000
FEEDBACK_APP_VERSION_MAX_LENGTH: Final = 64
FEEDBACK_GAME_TITLE_MAX_LENGTH: Final = 255
# Matches `users.username`.
FEEDBACK_USERNAME_MAX_LENGTH: Final = 255

FEEDBACK_RATE_LIMIT_MAX_REQUESTS: Final = 5
FEEDBACK_RATE_LIMIT_WINDOW_SECONDS: Final = 60 * 60


class Feedback(BaseModel):
    """A note a signed-in user sent to the administrators."""

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_created_at", "created_at"),
        Index("ix_feedback_kind", "kind"),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Null for the kiosk guest, who is not a users row, and after the account is deleted.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    username: Mapped[str] = mapped_column(
        String(FEEDBACK_USERNAME_MAX_LENGTH), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(FEEDBACK_KIND_MAX_LENGTH), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_path: Mapped[str] = mapped_column(
        String(FEEDBACK_PAGE_PATH_MAX_LENGTH), nullable=False
    )
    app_version: Mapped[str] = mapped_column(
        String(FEEDBACK_APP_VERSION_MAX_LENGTH), nullable=False
    )
    platform_id: Mapped[int | None] = mapped_column(
        ForeignKey("platforms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    game_title: Mapped[str | None] = mapped_column(
        String(FEEDBACK_GAME_TITLE_MAX_LENGTH), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)

    platform: Mapped[Platform | None] = relationship(lazy="raise")
