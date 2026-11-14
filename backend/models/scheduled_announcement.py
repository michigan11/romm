from datetime import datetime

from sqlalchemy import TIMESTAMP, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.announcement import ANNOUNCEMENT_TITLE_MAX_LENGTH
from models.base import BaseModel


class ScheduledAnnouncement(BaseModel):
    """A notice that replaces the current announcement at `starts_at`."""

    __tablename__ = "scheduled_announcements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(ANNOUNCEMENT_TITLE_MAX_LENGTH), default="", nullable=False
    )
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    ends_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # The revision published for this schedule. A later edit moves it, so the
    # end time leaves that edit in place.
    activated_revision: Mapped[int | None] = mapped_column(Integer)
    ended_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
