from fastapi import HTTPException, Request, status

from decorators.auth import protected_route
from endpoints.responses.scheduled_announcement import (
    ScheduledAnnouncementSchema,
    ScheduledAnnouncementWrite,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin
from handler.database import db_scheduled_announcement_handler
from handler.database.scheduled_announcements_handler import ScheduledAnnouncementLocked
from models.scheduled_announcement import ScheduledAnnouncement
from utils.router import APIRouter

router = APIRouter(
    prefix="/scheduled-announcements",
    tags=["scheduled-announcements"],
)

_NOT_FOUND = "Scheduled announcement not found"
_LOCKED = "This scheduled announcement has already gone live"


def _schema(row: ScheduledAnnouncement) -> ScheduledAnnouncementSchema:
    return ScheduledAnnouncementSchema.model_validate(row)


@protected_route(router.get, "", [Scope.USERS_WRITE])
def list_scheduled_announcements(
    request: Request,
) -> list[ScheduledAnnouncementSchema]:
    """Schedules, including ones that already ran. Admins only."""
    assert_admin(request)
    db_scheduled_announcement_handler.apply_due()
    return [_schema(row) for row in db_scheduled_announcement_handler.list_all()]


@protected_route(
    router.post, "", [Scope.USERS_WRITE], status_code=status.HTTP_201_CREATED
)
def create_scheduled_announcement(
    request: Request, payload: ScheduledAnnouncementWrite
) -> ScheduledAnnouncementSchema:
    """Add a schedule. A start time that has already passed is published now."""
    assert_admin(request)
    row = db_scheduled_announcement_handler.create(
        title=payload.title,
        message=payload.message,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db_scheduled_announcement_handler.apply_due()
    stored = db_scheduled_announcement_handler.get(row.id)
    return _schema(stored or row)


@protected_route(router.put, "/{schedule_id}", [Scope.USERS_WRITE])
def update_scheduled_announcement(
    request: Request, schedule_id: int, payload: ScheduledAnnouncementWrite
) -> ScheduledAnnouncementSchema:
    """Replace a schedule that has not gone live."""
    assert_admin(request)
    db_scheduled_announcement_handler.apply_due()
    try:
        row = db_scheduled_announcement_handler.update(
            schedule_id,
            title=payload.title,
            message=payload.message,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
        )
    except ScheduledAnnouncementLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_LOCKED
        ) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    db_scheduled_announcement_handler.apply_due()
    stored = db_scheduled_announcement_handler.get(row.id)
    return _schema(stored or row)


@protected_route(
    router.delete,
    "/{schedule_id}",
    [Scope.USERS_WRITE],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_scheduled_announcement(request: Request, schedule_id: int) -> None:
    """Delete a schedule that has not gone live."""
    assert_admin(request)
    db_scheduled_announcement_handler.apply_due()
    try:
        found = db_scheduled_announcement_handler.delete(schedule_id)
    except ScheduledAnnouncementLocked as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_LOCKED
        ) from exc
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
