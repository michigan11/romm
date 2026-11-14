from fastapi import Request, status

from decorators.auth import protected_route
from endpoints.responses.announcement import (
    AnnouncementDismiss,
    AnnouncementSchema,
    AnnouncementUpdate,
)
from handler.auth.constants import Scope
from handler.auth.dependencies import assert_admin, get_permissions
from handler.database import (
    db_announcement_handler,
    db_scheduled_announcement_handler,
)
from models.announcement import Announcement
from utils.router import APIRouter

router = APIRouter(
    prefix="/announcement",
    tags=["announcement"],
)


def _pending(row: Announcement, dismissed: int | None) -> bool:
    return bool(
        row.enabled and row.message and (dismissed is None or dismissed < row.revision)
    )


def _schema(
    row: Announcement, dismissed: int | None, *, reveal: bool
) -> AnnouncementSchema:
    # A disabled draft stays on the server until an admin turns it on.
    if not reveal and not row.enabled:
        return AnnouncementSchema(
            enabled=False, title="", message="", revision=0, pending=False
        )
    return AnnouncementSchema(
        enabled=row.enabled,
        title=row.title,
        message=row.message,
        revision=row.revision,
        pending=_pending(row, dismissed),
    )


def _view(request: Request) -> AnnouncementSchema:
    row, dismissed = db_announcement_handler.state_for(request.user.id)
    return _schema(row, dismissed, reveal=get_permissions(request).is_admin)


@protected_route(router.get, "", [Scope.ME_READ])
def get_announcement(request: Request) -> AnnouncementSchema:
    """The current notice, after publishing any scheduled notice that is due. Disabled text is returned only to an admin."""
    db_scheduled_announcement_handler.apply_due()
    return _view(request)


@protected_route(router.put, "", [Scope.USERS_WRITE])
def update_announcement(
    request: Request, payload: AnnouncementUpdate
) -> AnnouncementSchema:
    """Replace the notice. Admins only, even when `users.write` is delegated."""
    assert_admin(request)
    db_announcement_handler.update(
        enabled=payload.enabled, title=payload.title, message=payload.message
    )
    return _view(request)


# Kiosk mode is read-only, so closing the dialog cannot require me.write.
@protected_route(
    router.post, "/dismiss", [Scope.ME_READ], status_code=status.HTTP_204_NO_CONTENT
)
def dismiss_announcement(request: Request, payload: AnnouncementDismiss) -> None:
    """Record the revision the caller closed."""
    db_announcement_handler.dismiss(request.user.id, payload.revision)
