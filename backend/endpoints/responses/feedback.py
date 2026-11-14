from typing import Self

from pydantic import field_validator, model_validator

from endpoints.responses.base import BaseModel, UTCDatetime
from models.feedback import (
    FEEDBACK_APP_VERSION_MAX_LENGTH,
    FEEDBACK_GAME_TITLE_MAX_LENGTH,
    FEEDBACK_MESSAGE_MAX_LENGTH,
    FEEDBACK_PAGE_PATH_MAX_LENGTH,
    FeedbackKind,
)


def _plain(value: str) -> str:
    """Drop characters a note cannot show, keeping tabs and newlines."""
    return "".join(ch for ch in value if ch in "\t\n" or ord(ch) >= 32)


def _single_line(value: str) -> str:
    return "".join(ch for ch in value if ord(ch) >= 32).strip()


class FeedbackSchema(BaseModel):
    id: int
    user_id: int | None
    username: str
    kind: FeedbackKind
    message: str
    page_path: str
    app_version: str
    platform_id: int | None
    platform_name: str | None
    game_title: str | None
    resolved: bool
    created_at: UTCDatetime
    updated_at: UTCDatetime


class FeedbackCreate(BaseModel):
    kind: FeedbackKind
    message: str
    page_path: str
    app_version: str = ""
    platform_id: int | None = None
    game_title: str | None = None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = _plain(value).strip()
        if not cleaned:
            raise ValueError("A message is required")
        if len(cleaned) > FEEDBACK_MESSAGE_MAX_LENGTH:
            raise ValueError(
                f"Message must be at most {FEEDBACK_MESSAGE_MAX_LENGTH} characters"
            )
        return cleaned

    @field_validator("page_path")
    @classmethod
    def clean_page_path(cls, value: str) -> str:
        cleaned = _single_line(value)
        if (
            not cleaned.startswith("/")
            or cleaned.startswith("//")
            or "://" in cleaned
            or len(cleaned) > FEEDBACK_PAGE_PATH_MAX_LENGTH
        ):
            raise ValueError("Page must be an in-app path")
        return cleaned

    @field_validator("app_version")
    @classmethod
    def clean_app_version(cls, value: str) -> str:
        cleaned = _single_line(value)
        if len(cleaned) > FEEDBACK_APP_VERSION_MAX_LENGTH:
            raise ValueError(
                f"Version must be at most {FEEDBACK_APP_VERSION_MAX_LENGTH} characters"
            )
        return cleaned

    @field_validator("game_title")
    @classmethod
    def clean_game_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = _single_line(value)
        if not cleaned:
            return None
        if len(cleaned) > FEEDBACK_GAME_TITLE_MAX_LENGTH:
            raise ValueError(
                f"Game title must be at most {FEEDBACK_GAME_TITLE_MAX_LENGTH} characters"
            )
        return cleaned

    @model_validator(mode="after")
    def only_requests_name_a_game(self) -> Self:
        if self.kind is not FeedbackKind.REQUEST:
            self.platform_id = None
            self.game_title = None
        return self


class FeedbackUpdate(BaseModel):
    resolved: bool
