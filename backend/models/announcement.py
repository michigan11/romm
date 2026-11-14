from typing import Final

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import BaseModel

# One row, so a missing id can be recreated without colliding with another.
ANNOUNCEMENT_ID: Final = 1

ANNOUNCEMENT_TITLE_MAX_LENGTH: Final = 255
ANNOUNCEMENT_MESSAGE_MAX_LENGTH: Final = 4000


class Announcement(BaseModel):
    """The server-wide notice. `revision` increments when the title or message changes."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    title: Mapped[str] = mapped_column(
        String(ANNOUNCEMENT_TITLE_MAX_LENGTH), default="", nullable=False
    )
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AnnouncementDismissal(BaseModel):
    """The revision a user has already closed."""

    __tablename__ = "announcement_dismissals"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
