from datetime import timedelta

from fastapi import status

from config import OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS
from handler.auth.base_handler import oauth_handler
from handler.auth.constants import Scope
from handler.database import db_announcement_handler, db_user_handler
from handler.database.base_handler import sync_session
from models.announcement import (
    ANNOUNCEMENT_MESSAGE_MAX_LENGTH,
    ANNOUNCEMENT_TITLE_MAX_LENGTH,
    AnnouncementDismissal,
)
from models.permission import (
    PermAction,
    PermEntity,
    PermissionGroup,
    PermissionGroupGrant,
)
from models.user import KIOSK_USER_ID, User


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


def _notice(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "enabled": True,
        "title": "Heads up",
        "message": "PS2 games stream, with one session per slot.",
    }
    body.update(overrides)
    return body


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/announcement").status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.put("/api/announcement", json=_notice()).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.post("/api/announcement/dismiss", json={"revision": 1}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_viewer_reads_the_default_and_cannot_change_it(
    client, access_token, viewer_access_token
):
    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    admin = client.get("/api/announcement", headers=_auth(access_token))

    assert viewer.status_code == status.HTTP_200_OK
    assert viewer.json() == {
        "enabled": False,
        "title": "",
        "message": "",
        "revision": 0,
        "pending": False,
    }
    assert admin.json() == viewer.json()

    denied = client.put(
        "/api/announcement", json=_notice(), headers=_auth(viewer_access_token)
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN


def test_editor_cannot_change_it(client, editor_access_token):
    denied = client.put(
        "/api/announcement", json=_notice(), headers=_auth(editor_access_token)
    )
    assert denied.status_code == status.HTTP_403_FORBIDDEN


def test_delegated_users_write_cannot_change_it(client, viewer_user: User):
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

        denied = client.put(
            "/api/announcement", json=_notice(), headers=_auth(_token(user))
        )
        assert denied.status_code == status.HTTP_403_FORBIDDEN
        assert denied.json()["detail"] == "Administrator privileges required"
    finally:
        with sync_session.begin() as session:
            session.query(PermissionGroup).filter_by(id=group_id).delete()


def test_users_see_a_published_notice_once(
    client, access_token, viewer_access_token, editor_access_token
):
    published = client.put(
        "/api/announcement", json=_notice(), headers=_auth(access_token)
    )
    assert published.status_code == status.HTTP_200_OK
    assert published.json()["revision"] == 1
    assert published.json()["pending"] is True

    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json()["pending"] is True
    assert viewer.json()["message"] == _notice()["message"]

    dismissed = client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )
    assert dismissed.status_code == status.HTTP_204_NO_CONTENT
    assert (
        client.get("/api/announcement", headers=_auth(viewer_access_token)).json()[
            "pending"
        ]
        is False
    )
    # Closing it is per user.
    assert (
        client.get("/api/announcement", headers=_auth(editor_access_token)).json()[
            "pending"
        ]
        is True
    )


def test_a_text_change_shows_the_notice_again(
    client, access_token, viewer_access_token
):
    client.put("/api/announcement", json=_notice(), headers=_auth(access_token))
    client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )

    changed = client.put(
        "/api/announcement",
        json=_notice(message="Older platforms play in the browser."),
        headers=_auth(access_token),
    )
    assert changed.json()["revision"] == 2
    assert (
        client.get("/api/announcement", headers=_auth(viewer_access_token)).json()[
            "pending"
        ]
        is True
    )

    client.post(
        "/api/announcement/dismiss",
        json={"revision": 2},
        headers=_auth(viewer_access_token),
    )
    titled = client.put(
        "/api/announcement",
        json=_notice(
            title="How to play", message="Older platforms play in the browser."
        ),
        headers=_auth(access_token),
    )
    assert titled.json()["revision"] == 3
    assert (
        client.get("/api/announcement", headers=_auth(viewer_access_token)).json()[
            "pending"
        ]
        is True
    )


def test_reenabling_the_same_text_stays_dismissed(
    client, access_token, viewer_access_token
):
    client.put("/api/announcement", json=_notice(), headers=_auth(access_token))
    client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )
    client.put(
        "/api/announcement",
        json=_notice(enabled=False),
        headers=_auth(access_token),
    )
    hidden = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert hidden.json()["enabled"] is False
    assert hidden.json()["message"] == ""

    again = client.put("/api/announcement", json=_notice(), headers=_auth(access_token))
    assert again.json()["revision"] == 1
    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json()["pending"] is False
    assert viewer.json()["message"] == _notice()["message"]


def test_a_disabled_draft_is_hidden_from_non_admins(
    client, access_token, viewer_access_token
):
    draft = "Not ready yet."
    saved = client.put(
        "/api/announcement",
        json=_notice(enabled=False, message=draft),
        headers=_auth(access_token),
    )
    assert saved.json()["message"] == draft
    assert saved.json()["pending"] is False

    viewer = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert viewer.json() == {
        "enabled": False,
        "title": "",
        "message": "",
        "revision": 0,
        "pending": False,
    }


def test_equivalent_text_does_not_bump_the_revision(client, access_token):
    first = client.put("/api/announcement", json=_notice(), headers=_auth(access_token))
    assert first.json()["revision"] == 1

    same = client.put(
        "/api/announcement",
        json=_notice(
            title="  Heads up  ",
            message="PS2 games stream, with one session per slot.\x00",
        ),
        headers=_auth(access_token),
    )
    assert same.status_code == status.HTTP_200_OK
    assert same.json()["revision"] == 1
    assert same.json()["title"] == "Heads up"


def test_enabling_without_a_message_is_rejected(client, access_token):
    empty = client.put(
        "/api/announcement",
        json=_notice(message="   "),
        headers=_auth(access_token),
    )
    assert empty.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    too_long = client.put(
        "/api/announcement",
        json=_notice(message="x" * (ANNOUNCEMENT_MESSAGE_MAX_LENGTH + 1)),
        headers=_auth(access_token),
    )
    assert too_long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    title = client.put(
        "/api/announcement",
        json=_notice(title="t" * (ANNOUNCEMENT_TITLE_MAX_LENGTH + 1)),
        headers=_auth(access_token),
    )
    assert title.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_dismissing_an_older_revision_keeps_the_new_one(
    client, access_token, viewer_access_token
):
    client.put("/api/announcement", json=_notice(), headers=_auth(access_token))
    client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )
    client.put(
        "/api/announcement",
        json=_notice(message="A second version."),
        headers=_auth(access_token),
    )

    client.post(
        "/api/announcement/dismiss",
        json={"revision": 1},
        headers=_auth(viewer_access_token),
    )
    still = client.get("/api/announcement", headers=_auth(viewer_access_token))
    assert still.json()["revision"] == 2
    assert still.json()["pending"] is True


def test_kiosk_dismiss_writes_nothing():
    db_announcement_handler.update(
        enabled=True, title="", message="Hello from the lobby."
    )
    db_announcement_handler.dismiss(KIOSK_USER_ID, 1)

    with sync_session() as session:
        assert session.get(AnnouncementDismissal, KIOSK_USER_ID) is None
