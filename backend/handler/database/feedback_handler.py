from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from decorators.database import INJECTED_SESSION, begin_session
from models.feedback import Feedback, FeedbackKind

from .base_handler import DBBaseHandler


def _with_platform() -> LoaderOption:
    # Name only. Built per query so importing this module does not configure mappers.
    from models.platform import Platform

    return joinedload(Feedback.platform).load_only(
        Platform.id, Platform.name, Platform.custom_name
    )


class DBFeedbackHandler(DBBaseHandler):
    @begin_session
    def add(
        self,
        *,
        user_id: int | None,
        username: str,
        kind: FeedbackKind,
        message: str,
        page_path: str,
        app_version: str,
        platform_id: int | None,
        game_title: str | None,
        session: Session = INJECTED_SESSION,
    ) -> Feedback:
        """Store a note and return it with its platform loaded."""
        row = Feedback(
            user_id=user_id,
            username=username,
            kind=kind.value,
            message=message,
            page_path=page_path,
            app_version=app_version,
            platform_id=platform_id,
            game_title=game_title,
            resolved=False,
        )
        session.add(row)
        session.flush()
        stored = self.get(row.id, session=session)
        if stored is None:
            return row
        return stored

    @begin_session
    def get(
        self, feedback_id: int, session: Session = INJECTED_SESSION
    ) -> Feedback | None:
        return (
            session.scalars(
                select(Feedback)
                .options(_with_platform())
                .where(Feedback.id == feedback_id)
            )
            .unique()
            .one_or_none()
        )

    @begin_session
    def list_feedback(
        self,
        *,
        kind: FeedbackKind | None,
        limit: int,
        offset: int,
        session: Session = INJECTED_SESSION,
    ) -> tuple[Sequence[Feedback], int]:
        """Notes newest first, optionally one kind, and how many match."""
        filters = [] if kind is None else [Feedback.kind == kind.value]
        total = session.scalar(
            select(func.count()).select_from(Feedback).where(*filters)
        )
        rows = (
            session.scalars(
                select(Feedback)
                .options(_with_platform())
                .where(*filters)
                .order_by(Feedback.created_at.desc(), Feedback.id.desc())
                .limit(limit)
                .offset(offset)
            )
            .unique()
            .all()
        )
        return rows, int(total or 0)

    @begin_session
    def set_resolved(
        self,
        feedback_id: int,
        resolved: bool,
        session: Session = INJECTED_SESSION,
    ) -> Feedback | None:
        row = session.get(Feedback, feedback_id)
        if row is None:
            return None
        row.resolved = resolved
        session.flush()
        return self.get(feedback_id, session=session)

    @begin_session
    def delete(self, feedback_id: int, session: Session = INJECTED_SESSION) -> bool:
        row = session.get(Feedback, feedback_id)
        if row is None:
            return False
        session.delete(row)
        return True
