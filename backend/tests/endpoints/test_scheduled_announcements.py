from datetime import datetime, timedelta, timezone

from fastapi import status

from config import OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS
from handler.auth.base_handler import oauth_handler
from handler.auth.constants import Scope
from handler.database import db_announcement_handler, db_user_handler
from handler.database.base_handler import sync_session
from models.announcement import ANNOUNCEMENT_MESSAGE_MAX_LENGTH
from models.permission import (
    PermAction,
    PermEntity,
    PermissionGroup,
    PermissionGroupGrant,
)
from models.user import User


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _token(user: User) -> str:
    return oauth_handler.create_access_token(
        data={
            "sub": user.username,
            "iss": "romm:oauth",
            "scopes": " ".join(user.oauth_scopes),
        },
        expires_delta=timedelta(seconds=OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS),
    )


def _at(**delta: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()


def _schedule(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Maintenance",
        "message": "The library is briefly unavailable.",
        "starts_at": _at(hours=2),
        "ends_at": _at(hours=3),
    }
    body.update(overrides)
    return body


def test_unauthenticated_requests_are_rejected(client):
    assert (
        client.get("/api/scheduled-announcements").status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.post("/api/scheduled-announcements", json=_schedule()).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.put("/api/scheduled-announcements/1", json=_schedule()).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.delete("/api/scheduled-announcements/1").status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_viewer_cannot_read_or_change_schedules(client, viewer_access_token):
    listed = client.get(
        "/api/scheduled-announcements", headers=_auth(viewer_access_token)
    )
    created = client.post(
        "/api/scheduled-announcements",
        json=_schedule(),
        headers=_auth(viewer_access_token),
    )
    assert listed.status_code == status.HTTP_403_FORBIDDEN
    assert created.status_code == status.HTTP_403_FORBIDDEN


def test_editor_cannot_change_schedules(client, editor_access_token):
    denied = client.post(
        "/api/scheduled-announcements",
        json=_schedule(),
        headers=_auth(editor_access_token),
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN


def test_delegated_users_write_cannot_change_schedules(client, viewer_user: User):
    with sync_session.begin() as session:
        group = PermissionGroup(
            name="User managers",
            grants=[
                PermissionGroupGrant(entity=PermEntity.USERS, action=PermAction.WRITE)
            ],
        )
        session.add(group)
        session.flush()
        group_id = group.id
    try:
        db_user_handler.update_user(viewer_user.id, {"permission_group_id": group_id})
        user = db_user_handler.get_user(viewer_user.id)
        assert user is not None
        assert Scope.USERS_WRITE in user.oauth_scopes

        denied = client.post(
            "/api/scheduled-announcements",
            json=_schedule(),
            headers=_auth(_token(user)),
        )
        assert denied.status_code == status.HTTP_403_FORBIDDEN
        assert denied.json()["detail"] == "Administrator privileges required"
    finally:
        with sync_session.begin() as session:
            session.query(PermissionGroup).filter_by(id=group_id).delete()


def test_admin_creates_edits_and_deletes_before_it_goes_live(client, access_token):
    created = client.post(
        "/api/scheduled-announcements",
        json=_schedule(),
        headers=_auth(access_token),
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["activated_at"] is None
    assert body["title"] == "Maintenance"
    schedule_id = body["id"]

    listed = client.get("/api/scheduled-announcements", headers=_auth(access_token))
    assert listed.status_code == status.HTTP_200_OK
    assert [row["id"] for row in listed.json()] == [schedule_id]

    edited = client.put(
        f"/api/scheduled-announcements/{schedule_id}",
        json=_schedule(title="Tonight", message="Back online by morning."),
        headers=_auth(access_token),
    )
    assert edited.status_code == status.HTTP_200_OK
    assert edited.json()["title"] == "Tonight"
    assert edited.json()["activated_at"] is None

    removed = client.delete(
        f"/api/scheduled-announcements/{schedule_id}", headers=_auth(access_token)
    )
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert (
        client.get("/api/scheduled-announcements", headers=_auth(access_token)).json()
        == []
    )


def test_a_future_schedule_does_not_change_the_current_notice(client, access_token):
    client.post(
        "/api/scheduled-announcements",
        json=_schedule(),
        headers=_auth(access_token),
    )
    current = client.get("/api/announcement", headers=_auth(access_token))
    assert current.json()["enabled"] is False
    assert current.json()["message"] == ""
    assert current.json()["revision"] == 0


def test_a_due_schedule_publishes_once(client, access_token, viewer_access_token):
    created = client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at=_at(minutes=-5), ends_at=None),
        headers=_auth(access_token),
    )
    assert created.json()["activated_at"] is not None
    assert created.json()["ended_at"] is None

    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json()["enabled"] is True
    assert viewer.json()["pending"] is True
    assert viewer.json()["message"] == _schedule()["message"]
    assert viewer.json()["revision"] == 1

    again = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert again.json()["revision"] == 1

    locked = client.delete(
        f"/api/scheduled-announcements/{created.json()['id']}",
        headers=_auth(access_token),
    )
    assert locked.status_code == status.HTTP_409_CONFLICT
    edited = client.put(
        f"/api/scheduled-announcements/{created.json()['id']}",
        json=_schedule(starts_at=_at(minutes=-5), ends_at=None, message="Too late."),
        headers=_auth(access_token),
    )
    assert edited.status_code == status.HTTP_409_CONFLICT


def test_publishing_the_same_text_shows_it_again(
    client, access_token, viewer_access_token
):
    message = "The library is briefly unavailable."
    client.put(
        "/api/announcement",
        json={"enabled": True, "title": "Maintenance", "message": message},
        headers=_auth(access_token),
    )
    client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )

    client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at=_at(minutes=-1), ends_at=None, message=message),
        headers=_auth(access_token),
    )
    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json()["revision"] == 2
    assert viewer.json()["pending"] is True
    assert viewer.json()["message"] == message


def test_an_end_time_disables_only_the_notice_that_schedule_set(
    client, access_token, viewer_access_token
):
    created = client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at=_at(minutes=-30), ends_at=_at(minutes=-1)),
        headers=_auth(access_token),
    )
    assert created.json()["ended_at"] is not None

    hidden = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert hidden.json()["enabled"] is False
    assert hidden.json()["message"] == ""
    admin = client.get("/api/announcement", headers=_auth(access_token))
    assert admin.json()["enabled"] is False
    assert admin.json()["message"] == _schedule()["message"]
    assert admin.json()["revision"] == 1

    # A second pass does not publish it again.
    client.get("/api/announcement", headers=_auth(access_token))
    assert (
        client.get("/api/announcement", headers=_auth(access_token)).json()["revision"]
        == 1
    )


def test_an_end_time_leaves_a_later_edit_in_place(client, access_token):
    client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at=_at(minutes=-20), ends_at=_at(minutes=20)),
        headers=_auth(access_token),
    )
    published = client.get("/api/announcement", headers=_auth(access_token))
    assert published.json()["enabled"] is True
    assert published.json()["revision"] == 1

    client.put(
        "/api/announcement",
        json={
            "enabled": True,
            "title": "Maintenance",
            "message": "An admin rewrote this.",
        },
        headers=_auth(access_token),
    )
    from handler.database import db_scheduled_announcement_handler

    db_scheduled_announcement_handler.apply_due(
        datetime.now(timezone.utc) + timedelta(hours=1)
    )

    current = client.get("/api/announcement", headers=_auth(access_token))
    assert current.json()["enabled"] is True
    assert current.json()["message"] == "An admin rewrote this."
    assert current.json()["revision"] == 2


def test_overlapping_schedules_leave_the_latest_one_active(client, access_token):
    client.post(
        "/api/scheduled-announcements",
        json=_schedule(
            title="First",
            message="The first window.",
            starts_at=_at(hours=-3),
            ends_at=_at(hours=-2),
        ),
        headers=_auth(access_token),
    )
    client.post(
        "/api/scheduled-announcements",
        json=_schedule(
            title="Second",
            message="The second window.",
            starts_at=_at(minutes=-30),
            ends_at=None,
        ),
        headers=_auth(access_token),
    )

    current = client.get("/api/announcement", headers=_auth(access_token))
    assert current.json()["enabled"] is True
    assert current.json()["title"] == "Second"
    assert current.json()["message"] == "The second window."
    assert current.json()["revision"] == 2


def test_a_window_that_already_closed_ends_disabled(client, access_token):
    client.post(
        "/api/scheduled-announcements",
        json=_schedule(
            message="Already over.",
            starts_at=_at(hours=-2),
            ends_at=_at(hours=-1),
        ),
        headers=_auth(access_token),
    )
    current = client.get("/api/announcement", headers=_auth(access_token))
    assert current.json()["enabled"] is False
    assert current.json()["message"] == "Already over."


def test_invalid_schedules_are_rejected(client, access_token):
    empty = client.post(
        "/api/scheduled-announcements",
        json=_schedule(message="   "),
        headers=_auth(access_token),
    )
    assert empty.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    too_long = client.post(
        "/api/scheduled-announcements",
        json=_schedule(message="x" * (ANNOUNCEMENT_MESSAGE_MAX_LENGTH + 1)),
        headers=_auth(access_token),
    )
    assert too_long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    backwards = client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at=_at(hours=3), ends_at=_at(hours=1)),
        headers=_auth(access_token),
    )
    assert backwards.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    naive = client.post(
        "/api/scheduled-announcements",
        json=_schedule(starts_at="2026-12-01T09:30:00"),
        headers=_auth(access_token),
    )
    assert naive.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    missing = client.delete(
        "/api/scheduled-announcements/9999", headers=_auth(access_token)
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_reading_the_notice_publishes_a_due_schedule(client, viewer_access_token):
    from handler.database import db_scheduled_announcement_handler

    db_scheduled_announcement_handler.create(
        title="Maintenance",
        message="Published when someone signs in.",
        starts_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        ends_at=None,
    )
    hidden = client.get(
        "/api/scheduled-announcements", headers=_auth(viewer_access_token)
    )
    assert hidden.status_code == status.HTTP_403_FORBIDDEN

    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json()["enabled"] is True
    assert viewer.json()["pending"] is True
    assert viewer.json()["message"] == "Published when someone signs in."
    assert viewer.json()["revision"] == 1


def test_apply_due_is_idempotent_for_the_handler():
    from handler.database import db_scheduled_announcement_handler
    from models.user import KIOSK_USER_ID

    db_scheduled_announcement_handler.create(
        title="Once",
        message="Published a single time.",
        starts_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        ends_at=None,
    )
    db_scheduled_announcement_handler.apply_due()
    db_scheduled_announcement_handler.apply_due()

    notice, _dismissed = db_announcement_handler.state_for(KIOSK_USER_ID)
    assert notice.revision == 1
    assert notice.enabled is True
