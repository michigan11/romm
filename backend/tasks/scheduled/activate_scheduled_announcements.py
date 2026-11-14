from handler.database import db_scheduled_announcement_handler
from tasks.registry import ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC
from tasks.tasks import PeriodicTask


class ActivateScheduledAnnouncementsTask(PeriodicTask):
    def __init__(self) -> None:
        super().__init__(ACTIVATE_SCHEDULED_ANNOUNCEMENTS_SPEC)

    async def run(self) -> None:
        if not self.spec.enabled:
            return
        db_scheduled_announcement_handler.apply_due()


activate_scheduled_announcements_task = ActivateScheduledAnnouncementsTask()
