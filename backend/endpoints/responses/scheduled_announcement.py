from datetime import datetime, timezone
from typing import Self

from pydantic import ConfigDict, field_validator, model_validator

from endpoints.responses.base import BaseModel, UTCDatetime
from models.announcement import (
    ANNOUNCEMENT_MESSAGE_MAX_LENGTH,
    ANNOUNCEMENT_TITLE_MAX_LENGTH,
)


def _plain(value: str) -> str:
    """Drop characters a notice cannot show, keeping tabs and newlines."""
    return "".join(ch for ch in value if ch in "\t\n" or ord(ch) >= 32)


class ScheduledAnnouncementSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    starts_at: UTCDatetime
    ends_at: UTCDatetime | None
    activated_at: UTCDatetime | None
    ended_at: UTCDatetime | None


class ScheduledAnnouncementWrite(BaseModel):
    title: str = ""
    message: str
    starts_at: datetime
    ends_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        cleaned = " ".join(_plain(value).split())
        if len(cleaned) > ANNOUNCEMENT_TITLE_MAX_LENGTH:
            raise ValueError(
                f"Title must be at most {ANNOUNCEMENT_TITLE_MAX_LENGTH} characters"
            )
        return cleaned

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = _plain(value).strip()
        if len(cleaned) > ANNOUNCEMENT_MESSAGE_MAX_LENGTH:
            raise ValueError(
                f"Message must be at most {ANNOUNCEMENT_MESSAGE_MAX_LENGTH} characters"
            )
        if not cleaned:
            raise ValueError("A message is required")
        return cleaned

    @field_validator("starts_at", "ends_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("A timezone is required")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def end_after_start(self) -> Self:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("The end time has to be after the start time")
        return self
