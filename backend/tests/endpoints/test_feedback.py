from datetime import timedelta
from unittest.mock import patch

from fastapi import status

from config import OAUTH_ACCESS_TOKEN_EXPIRE_SECONDS
from handler.auth.base_handler import oauth_handler
from handler.auth.constants import Scope
from handler.database import db_user_handler
from handler.database.base_handler import sync_session
from models.feedback import (
    FEEDBACK_MESSAGE_MAX_LENGTH,
    FEEDBACK_RATE_LIMIT_MAX_REQUESTS,
)
from models.permission import (
    HiddenEntity,
    PermAction,
    PermEntity,
    PermissionGroup,
    PermissionGroupGrant,
)
from models.platform import Platform
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


def _note(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "kind": "bug",
        "message": "The cover never loads on the gallery.",
        "page_path": "/gallery",
        "app_version": "5.4.1",
    }
    body.update(overrides)
    return body


def test_unauthenticated_requests_are_rejected(client):
    assert (
        client.post("/api/feedback", json=_note()).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert client.get("/api/feedback").status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.patch("/api/feedback/1", json={"resolved": True}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert client.delete("/api/feedback/1").status_code == status.HTTP_401_UNAUTHORIZED


def test_a_viewer_can_send_and_cannot_manage(client, viewer_access_token, access_token):
    created = client.post(
        "/api/feedback", json=_note(), headers=_auth(viewer_access_token)
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["username"] == "test_viewer"
    assert body["kind"] == "bug"
    assert body["message"] == _note()["message"]
    assert body["page_path"] == "/gallery"
    assert body["app_version"] == "5.4.1"
    assert body["resolved"] is False
    assert body["platform_id"] is None
    assert body["game_title"] is None

    assert (
        client.get("/api/feedback", headers=_auth(viewer_access_token)).status_code
        == status.HTTP_403_FORBIDDEN
    )
    assert (
        client.patch(
            f"/api/feedback/{body['id']}",
            json={"resolved": True},
            headers=_auth(viewer_access_token),
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )
    assert (
        client.delete(
            f"/api/feedback/{body['id']}", headers=_auth(viewer_access_token)
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )

    listed = client.get("/api/feedback", headers=_auth(access_token))
    assert listed.status_code == status.HTTP_200_OK
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == body["id"]


def test_an_editor_cannot_list(client, editor_access_token):
    assert (
        client.get("/api/feedback", headers=_auth(editor_access_token)).status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_delegated_users_write_cannot_manage(
    client, viewer_user: User, viewer_access_token
):
    created = client.post(
        "/api/feedback", json=_note(), headers=_auth(viewer_access_token)
    )
    assert created.status_code == status.HTTP_201_CREATED
    feedback_id = created.json()["id"]

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
        headers = _auth(_token(user))

        listed = client.get("/api/feedback", headers=headers)
        assert listed.status_code == status.HTTP_403_FORBIDDEN
        assert listed.json()["detail"] == "Administrator privileges required"
        updated = client.patch(
            f"/api/feedback/{feedback_id}", json={"resolved": True}, headers=headers
        )
        assert updated.status_code == status.HTTP_403_FORBIDDEN
        deleted = client.delete(f"/api/feedback/{feedback_id}", headers=headers)
        assert deleted.status_code == status.HTTP_403_FORBIDDEN
    finally:
        with sync_session.begin() as session:
            session.query(PermissionGroup).filter_by(id=group_id).delete()


def test_admins_list_newest_first_and_can_resolve_and_delete(
    client, access_token, viewer_access_token
):
    headers = _auth(access_token)
    client.post(
        "/api/feedback",
        json=_note(message="Older note"),
        headers=_auth(viewer_access_token),
    )
    newer = client.post(
        "/api/feedback", json=_note(message="Newer note"), headers=headers
    )
    assert newer.status_code == status.HTTP_201_CREATED
    newer_id = newer.json()["id"]

    listed = client.get("/api/feedback", headers=headers)
    assert [item["message"] for item in listed.json()["items"]] == [
        "Newer note",
        "Older note",
    ]

    resolved = client.patch(
        f"/api/feedback/{newer_id}", json={"resolved": True}, headers=headers
    )
    assert resolved.status_code == status.HTTP_200_OK
    assert resolved.json()["resolved"] is True
    reopened = client.patch(
        f"/api/feedback/{newer_id}", json={"resolved": False}, headers=headers
    )
    assert reopened.json()["resolved"] is False

    missing = client.patch(
        "/api/feedback/999999", json={"resolved": True}, headers=headers
    )
    assert missing.status_code == status.HTTP_404_NOT_FOUND

    deleted = client.delete(f"/api/feedback/{newer_id}", headers=headers)
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    again = client.delete(f"/api/feedback/{newer_id}", headers=headers)
    assert again.status_code == status.HTTP_404_NOT_FOUND
    assert client.get("/api/feedback", headers=headers).json()["total"] == 1


def test_kind_filter_returns_only_that_kind(client, access_token):
    headers = _auth(access_token)
    client.post("/api/feedback", json=_note(kind="bug"), headers=headers)
    client.post(
        "/api/feedback",
        json=_note(kind="request", message="Please add it.", game_title="Ico"),
        headers=headers,
    )

    listed = client.get("/api/feedback", params={"kind": "request"}, headers=headers)
    assert listed.status_code == status.HTTP_200_OK
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["kind"] == "request"
    assert listed.json()["items"][0]["game_title"] == "Ico"


def test_a_game_request_keeps_the_platform_and_title(
    client, access_token, platform: Platform
):
    created = client.post(
        "/api/feedback",
        json=_note(
            kind="request",
            message="The library is missing this one.",
            platform_id=platform.id,
            game_title="  Shadow of the Colossus  ",
        ),
        headers=_auth(access_token),
    )
    assert created.status_code == status.HTTP_201_CREATED
    body = created.json()
    assert body["kind"] == "request"
    assert body["platform_id"] == platform.id
    assert body["platform_name"] == platform.name
    assert body["game_title"] == "Shadow of the Colossus"


def test_other_kinds_drop_a_platform_and_title(
    client, access_token, platform: Platform
):
    created = client.post(
        "/api/feedback",
        json=_note(kind="idea", platform_id=platform.id, game_title="Ico"),
        headers=_auth(access_token),
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["platform_id"] is None
    assert created.json()["game_title"] is None


def test_a_hidden_platform_is_rejected(
    client, viewer_user: User, viewer_access_token, platform: Platform, access_token
):
    with sync_session.begin() as session:
        session.add(
            HiddenEntity(
                entity=PermEntity.PLATFORMS,
                entity_id=platform.id,
                user_id=viewer_user.id,
            )
        )

    denied = client.post(
        "/api/feedback",
        json=_note(kind="request", platform_id=platform.id, game_title="Ico"),
        headers=_auth(viewer_access_token),
    )
    assert denied.status_code == status.HTTP_404_NOT_FOUND
    assert client.get("/api/feedback", headers=_auth(access_token)).json()["total"] == 0


def test_an_unknown_platform_is_rejected(client, viewer_access_token):
    denied = client.post(
        "/api/feedback",
        json=_note(kind="request", platform_id=999999, game_title="Ico"),
        headers=_auth(viewer_access_token),
    )
    assert denied.status_code == status.HTTP_404_NOT_FOUND


def test_a_note_needs_a_message_a_page_and_a_length_limit(client, viewer_access_token):
    headers = _auth(viewer_access_token)
    empty = client.post("/api/feedback", json=_note(message="   "), headers=headers)
    assert empty.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    long = client.post(
        "/api/feedback",
        json=_note(message="x" * (FEEDBACK_MESSAGE_MAX_LENGTH + 1)),
        headers=headers,
    )
    assert long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    external = client.post(
        "/api/feedback",
        json=_note(page_path="https://example.com"),
        headers=headers,
    )
    assert external.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_sending_is_limited_per_user(client, viewer_access_token, access_token):
    headers = _auth(viewer_access_token)
    for _ in range(FEEDBACK_RATE_LIMIT_MAX_REQUESTS):
        assert (
            client.post("/api/feedback", json=_note(), headers=headers).status_code
            == status.HTTP_201_CREATED
        )
    limited = client.post("/api/feedback", json=_note(), headers=headers)
    assert limited.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # The cap is per user, so an admin can still send.
    assert (
        client.post(
            "/api/feedback", json=_note(), headers=_auth(access_token)
        ).status_code
        == status.HTTP_201_CREATED
    )
    assert (
        client.get("/api/feedback", headers=_auth(access_token)).json()["total"]
        == FEEDBACK_RATE_LIMIT_MAX_REQUESTS + 1
    )


def test_the_kiosk_guest_can_send(client, access_token):
    with patch("handler.auth.hybrid_auth.KIOSK_MODE", True):
        created = client.post("/api/feedback", json=_note())
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["user_id"] is None
    assert created.json()["username"] == "kiosk"

    listed = client.get("/api/feedback", headers=_auth(access_token))
    assert listed.json()["items"][0]["username"] == "kiosk"
