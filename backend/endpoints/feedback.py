from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status

from decorators.auth import protected_route
from endpoints.responses.base import PAGE_QUERY, LimitOffsetPage, PageParams
from endpoints.responses.feedback import FeedbackCreate, FeedbackSchema, FeedbackUpdate
from exceptions.endpoint_exceptions import PlatformNotFoundInDatabaseException
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin, assert_platform_visible
from handler.database import db_feedback_handler, db_platform_handler
from models.feedback import (
    FEEDBACK_RATE_LIMIT_MAX_REQUESTS,
    FEEDBACK_RATE_LIMIT_WINDOW_SECONDS,
    Feedback,
    FeedbackKind,
)
from utils import get_version
from utils.rate_limit import enforce_rate_limit
from utils.router import APIRouter

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _platform_name(row: Feedback) -> str | None:
    platform = row.platform
    if platform is None:
        return None
    return platform.custom_name or platform.name


def _schema(row: Feedback) -> FeedbackSchema:
    return FeedbackSchema(
        id=row.id,
        user_id=row.user_id,
        username=row.username,
        kind=FeedbackKind(row.kind),
        message=row.message,
        page_path=row.page_path,
        app_version=row.app_version,
        platform_id=row.platform_id,
        platform_name=_platform_name(row),
        game_title=row.game_title,
        resolved=row.resolved,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _missing(feedback_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Feedback with id '{feedback_id}' not found",
    )


@protected_route(router.post, "", [Scope.ME_READ], status_code=status.HTTP_201_CREATED)
def create_feedback(request: Request, payload: FeedbackCreate) -> FeedbackSchema:
    """Store a note from the signed-in user, including a kiosk guest."""
    platform_id = payload.platform_id
    if platform_id is not None:
        platform = db_platform_handler.get_platform(platform_id)
        if platform is None:
            raise PlatformNotFoundInDatabaseException(platform_id)
        assert_platform_visible(request, platform)

    # One bucket per account. Every kiosk visitor shares the guest id.
    enforce_rate_limit(
        f"feedback-rate:{request.user.id}",
        max_requests=FEEDBACK_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=FEEDBACK_RATE_LIMIT_WINDOW_SECONDS,
        detail=(
            f"You can send {FEEDBACK_RATE_LIMIT_MAX_REQUESTS} notes an hour. "
            "Try again later."
        ),
    )
    row = db_feedback_handler.add(
        # The kiosk guest is not a users row, so the note is stored without one.
        user_id=None if request.user.is_kiosk_guest else request.user.id,
        username=request.user.username,
        kind=payload.kind,
        message=payload.message,
        page_path=payload.page_path,
        app_version=payload.app_version or get_version(),
        platform_id=platform_id,
        game_title=payload.game_title,
    )
    return _schema(row)


@protected_route(router.get, "", [Scope.USERS_WRITE])
def list_feedback(
    request: Request,
    page: Annotated[PageParams, Depends(PAGE_QUERY)],
    kind: Annotated[FeedbackKind | None, Query()] = None,
) -> LimitOffsetPage[FeedbackSchema]:
    """Notes newest first. Admins only, even when `users.write` is delegated."""
    assert_admin(request)
    rows, total = db_feedback_handler.list_feedback(
        kind=kind, limit=page.limit, offset=page.offset
    )
    return LimitOffsetPage.create([_schema(row) for row in rows], page, total=total)


@protected_route(router.patch, "/{feedback_id}", [Scope.USERS_WRITE])
def update_feedback(
    request: Request, feedback_id: int, payload: FeedbackUpdate
) -> FeedbackSchema:
    """Mark a note resolved or unresolved. Admins only."""
    assert_admin(request)
    row = db_feedback_handler.set_resolved(feedback_id, payload.resolved)
    if row is None:
        raise _missing(feedback_id)
    return _schema(row)


@protected_route(
    router.delete,
    "/{feedback_id}",
    [Scope.USERS_WRITE],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_feedback(request: Request, feedback_id: int) -> None:
    """Remove a note. Admins only."""
    assert_admin(request)
    if not db_feedback_handler.delete(feedback_id):
        raise _missing(feedback_id)
