from typing import Self

from pydantic import Field, field_validator, model_validator

from endpoints.responses.base import BaseModel
from models.announcement import (
    ANNOUNCEMENT_MESSAGE_MAX_LENGTH,
    ANNOUNCEMENT_TITLE_MAX_LENGTH,
)


def _plain(value: str) -> str:
    """Drop characters a notice cannot show, keeping tabs and newlines."""
    return "".join(ch for ch in value if ch in "\t\n" or ord(ch) >= 32)


class AnnouncementSchema(BaseModel):
    enabled: bool
    title: str
    message: str
    revision: int
    # True when this caller should see the dialog.
    pending: bool


class AnnouncementUpdate(BaseModel):
    enabled: bool
    title: str = ""
    message: str = ""

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
        return cleaned

    @model_validator(mode="after")
    def enabled_needs_message(self) -> Self:
        if self.enabled and not self.message:
            raise ValueError("A message is required when the announcement is enabled")
        return self


class AnnouncementDismiss(BaseModel):
    revision: int = Field(ge=0)
