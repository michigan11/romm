from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from decorators.database import INJECTED_SESSION, begin_session
from logger.logger import log
from models.announcement import ANNOUNCEMENT_ID, Announcement
from models.scheduled_announcement import ScheduledAnnouncement

from .base_handler import DBBaseHandler


class ScheduledAnnouncementLocked(Exception):
    """The schedule has already gone live."""


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class DBScheduledAnnouncementsHandler(DBBaseHandler):
    @begin_session
    def list_all(
        self, session: Session = INJECTED_SESSION
    ) -> list[ScheduledAnnouncement]:
        """Every schedule, soonest start first."""
        return list(
            session.scalars(
                select(ScheduledAnnouncement).order_by(
                    ScheduledAnnouncement.starts_at, ScheduledAnnouncement.id
                )
            ).all()
        )

    @begin_session
    def get(
        self, schedule_id: int, session: Session = INJECTED_SESSION
    ) -> ScheduledAnnouncement | None:
        return session.get(ScheduledAnnouncement, schedule_id)

    @begin_session
    def create(
        self,
        *,
        title: str,
        message: str,
        starts_at: datetime,
        ends_at: datetime | None,
        session: Session = INJECTED_SESSION,
    ) -> ScheduledAnnouncement:
        """Store a schedule. It stays unpublished until its start time."""
        row = ScheduledAnnouncement(
            title=title,
            message=message,
            starts_at=_utc(starts_at),
            ends_at=_utc(ends_at) if ends_at is not None else None,
        )
        session.add(row)
        session.flush()
        return row

    @begin_session
    def update(
        self,
        schedule_id: int,
        *,
        title: str,
        message: str,
        starts_at: datetime,
        ends_at: datetime | None,
        session: Session = INJECTED_SESSION,
    ) -> ScheduledAnnouncement | None:
        """Replace a schedule that has not gone live. Missing rows return None."""
        row = session.get(ScheduledAnnouncement, schedule_id)
        if row is None:
            return None
        if row.activated_at is not None:
            raise ScheduledAnnouncementLocked()
        row.title = title
        row.message = message
        row.starts_at = _utc(starts_at)
        row.ends_at = _utc(ends_at) if ends_at is not None else None
        session.flush()
        return row

    @begin_session
    def delete(self, schedule_id: int, session: Session = INJECTED_SESSION) -> bool:
        """Delete a schedule that has not gone live. Missing rows return False."""
        row = session.get(ScheduledAnnouncement, schedule_id)
        if row is None:
            return False
        if row.activated_at is not None:
            raise ScheduledAnnouncementLocked()
        session.delete(row)
        return True

    @begin_session
    def apply_due(
        self,
        now: datetime | None = None,
        session: Session = INJECTED_SESSION,
    ) -> None:
        """Publish schedules whose start has passed, and end those that are finished."""
        moment = _utc(now or datetime.now(timezone.utc))
        # Lock the notice first so two publishers cannot interleave a revision bump.
        session.get(Announcement, ANNOUNCEMENT_ID, with_for_update=True)

        due = session.scalars(
            select(ScheduledAnnouncement)
            .where(ScheduledAnnouncement.activated_at.is_(None))
            .where(ScheduledAnnouncement.starts_at <= moment)
            .order_by(ScheduledAnnouncement.starts_at, ScheduledAnnouncement.id)
            .with_for_update()
        ).all()

        # Imported here so this module can load while the handler package initializes.
        from handler.database import db_announcement_handler

        published = 0
        for schedule in due:
            if schedule.activated_at is not None:
                continue
            # Same transaction as the schedule row, so a crash cannot publish twice.
            notice = db_announcement_handler.update(
                enabled=True,
                title=schedule.title,
                message=schedule.message,
                bump_revision=True,
                session=session,
            )
            schedule.activated_at = moment
            schedule.activated_revision = notice.revision
            published += 1

        ending = session.scalars(
            select(ScheduledAnnouncement)
            .where(ScheduledAnnouncement.activated_at.is_not(None))
            .where(ScheduledAnnouncement.ended_at.is_(None))
            .where(ScheduledAnnouncement.ends_at.is_not(None))
            .where(ScheduledAnnouncement.ends_at <= moment)
            .order_by(ScheduledAnnouncement.ends_at, ScheduledAnnouncement.id)
            .with_for_update()
        ).all()
        finished = 0
        for schedule in ending:
            if schedule.ended_at is not None:
                continue
            current = session.get(Announcement, ANNOUNCEMENT_ID)
            if (
                current is not None
                and schedule.activated_revision is not None
                and current.revision == schedule.activated_revision
            ):
                db_announcement_handler.update(
                    enabled=False,
                    title=current.title,
                    message=current.message,
                    session=session,
                )
            schedule.ended_at = moment
            finished += 1

        if published or finished:
            log.info(
                f"Scheduled announcements published {published}, finished {finished}"
            )
