from sqlalchemy.orm import Session

from decorators.database import INJECTED_SESSION, begin_session
from models.announcement import ANNOUNCEMENT_ID, Announcement, AnnouncementDismissal
from models.user import KIOSK_USER_ID

from .base_handler import DBBaseHandler


def _empty() -> Announcement:
    return Announcement(
        id=ANNOUNCEMENT_ID,
        enabled=False,
        title="",
        message="",
        revision=0,
    )


class DBAnnouncementsHandler(DBBaseHandler):
    @begin_session
    def state_for(
        self,
        user_id: int,
        session: Session = INJECTED_SESSION,
    ) -> tuple[Announcement, int | None]:
        """The notice and the revision this user has closed, if any."""
        row = session.get(Announcement, ANNOUNCEMENT_ID) or _empty()
        if user_id == KIOSK_USER_ID:
            return row, None
        marker = session.get(AnnouncementDismissal, user_id)
        return row, marker.revision if marker else None

    @begin_session
    def update(
        self,
        *,
        enabled: bool,
        title: str,
        message: str,
        session: Session = INJECTED_SESSION,
    ) -> Announcement:
        """Store the notice. The revision moves only when the text changes."""
        row = session.get(Announcement, ANNOUNCEMENT_ID)
        if row is None:
            row = _empty()
            session.add(row)
        if title != row.title or message != row.message:
            row.revision += 1
        row.enabled = enabled
        row.title = title
        row.message = message
        session.flush()
        return row

    @begin_session
    def dismiss(
        self,
        user_id: int,
        revision: int,
        session: Session = INJECTED_SESSION,
    ) -> None:
        """Remember the revision this user closed, capped at the one that exists now."""
        # The kiosk guest is not a users row, so there is nowhere to store this.
        if user_id == KIOSK_USER_ID:
            return
        row = session.get(Announcement, ANNOUNCEMENT_ID)
        if row is None or not row.enabled or not row.message:
            return
        acknowledged = min(revision, row.revision)
        marker = session.get(AnnouncementDismissal, user_id)
        if marker is None:
            session.add(AnnouncementDismissal(user_id=user_id, revision=acknowledged))
            return
        if acknowledged > marker.revision:
            marker.revision = acknowledged
