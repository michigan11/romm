from datetime import datetime, timedelta, timezone

from handler.database import (
    db_announcement_handler,
    db_scheduled_announcement_handler,
)
from models.user import KIOSK_USER_ID
from tasks.registry import (
    ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC,
    SCHEDULED_TASKS,
)
from tasks.scheduled.activate_scheduled_announcements import (
    activate_scheduled_announcements_task,
)


def test_the_task_is_scheduled_every_minute():
    assert (
        SCHEDULED_TASKS["activate_scheduled_announcements"]
        is ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC
    )
    assert ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC.enabled is True
    assert ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC.cron_string == "* * * * *"
    assert ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC.result_ttl == 0


async def test_the_task_publishes_a_due_schedule_once():
    db_scheduled_announcement_handler.create(
        title="Maintenance",
        message="Down at midnight.",
        starts_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        ends_at=None,
    )

    await activate_scheduled_announcements_task.run()
    await activate_scheduled_announcements_task.run()

    notice, _dismissed = db_announcement_handler.state_for(KIOSK_USER_ID)
    assert notice.enabled is True
    assert notice.title == "Maintenance"
    assert notice.message == "Down at midnight."
    assert notice.revision == 1
