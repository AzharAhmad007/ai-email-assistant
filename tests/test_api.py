from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import api


@pytest.fixture
def client():
    with api.drafts_lock:
        api.drafts.clear()

    with TestClient(api.app) as test_client:
        yield test_client

    with api.drafts_lock:
        api.drafts.clear()


def add_draft(draft_id="test-draft"):
    api.drafts[draft_id] = {
        "recipient": "manager@example.com",
        "subject": "Leave Request",
        "body": "Please approve two days of leave.",
        "status": "pending",
        "approved": False,
    }
    return draft_id


def test_generate_email_creates_pending_draft(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "generate_email",
        lambda instructions: {
            "recipient": "manager@example.com",
            "subject": "Leave Request",
            "body": "Please approve two days of leave.",
        },
    )

    response = client.post(
        "/api/generate-email",
        json={"instructions": "Request two days of leave."},
    )

    assert response.status_code == 200
    draft_id = response.json()["draft_id"]
    assert api.drafts[draft_id]["status"] == "pending"
    assert api.drafts[draft_id]["approved"] is False


def test_approval_requires_explicit_confirmation(client):
    draft_id = add_draft()

    response = client.post(
        f"/api/drafts/{draft_id}/approve",
        json={"confirmation": "NO"},
    )

    assert response.status_code == 400
    assert api.drafts[draft_id]["approved"] is False


def test_sending_requires_approval(client, monkeypatch):
    draft_id = add_draft()
    send_email = Mock()
    monkeypatch.setattr(api, "send_email", send_email)

    response = client.post(
        f"/api/drafts/{draft_id}/send",
        json={"confirmation": "SEND"},
    )

    assert response.status_code == 403
    assert api.drafts[draft_id]["status"] == "pending"
    send_email.assert_not_called()


def test_changed_draft_loses_approval(client, monkeypatch):
    draft_id = add_draft()
    send_email = Mock()
    monkeypatch.setattr(api, "send_email", send_email)

    approval_response = client.post(
        f"/api/drafts/{draft_id}/approve",
        json={"confirmation": "APPROVE"},
    )
    assert approval_response.status_code == 200

    api.drafts[draft_id]["subject"] = "Changed after approval"
    response = client.post(
        f"/api/drafts/{draft_id}/send",
        json={"confirmation": "SEND"},
    )

    assert response.status_code == 403
    assert api.drafts[draft_id]["approved"] is False
    assert "approved_content_hash" not in api.drafts[draft_id]
    send_email.assert_not_called()


def test_approved_draft_can_only_be_sent_once(client, monkeypatch):
    draft_id = add_draft()
    send_email = Mock(return_value=True)
    monkeypatch.setattr(api, "send_email", send_email)

    approval_response = client.post(
        f"/api/drafts/{draft_id}/approve",
        json={"confirmation": "APPROVE"},
    )
    assert approval_response.status_code == 200

    response = client.post(
        f"/api/drafts/{draft_id}/send",
        json={"confirmation": "SEND"},
    )
    second_response = client.post(
        f"/api/drafts/{draft_id}/send",
        json={"confirmation": "SEND"},
    )

    assert response.status_code == 200
    assert api.drafts[draft_id]["status"] == "sent"
    assert second_response.status_code == 404
    send_email.assert_called_once_with(
        recipient="manager@example.com",
        subject="Leave Request",
        body="Please approve two days of leave.",
    )