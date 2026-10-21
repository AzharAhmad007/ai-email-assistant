import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app import email_sender


@pytest.mark.parametrize(
    ("recipient", "subject", "body"),
    [
        ("", "Test Subject", "Test Body"),
        ("test@example.com", "", "Test Body"),
        ("test@example.com", "Test Subject", "   "),
    ],
)
def test_send_email_rejects_empty_fields(
    recipient,
    subject,
    body,
):
    with pytest.raises(ValueError):
        email_sender.send_email(recipient, subject, body)


@pytest.mark.parametrize(
    "recipient",
    [
        "invalid-email",
        "missing-domain@",
        "missing-tld@example",
    ],
)
def test_send_email_rejects_invalid_recipient(recipient):
    with pytest.raises(ValueError, match="Invalid recipient"):
        email_sender.send_email(
            recipient,
            "Test Subject",
            "Test Body",
        )


@patch.object(email_sender, "get_gmail_credentials")
def test_send_email_rejects_missing_credentials(
    mock_credentials,
):
    mock_credentials.side_effect = ValueError(
        "Gmail credentials are missing."
    )

    with pytest.raises(ValueError, match="credentials are missing"):
        email_sender.send_email(
            "test@example.com",
            "Test Subject",
            "Test Body",
        )


@patch.object(email_sender.smtplib, "SMTP")
@patch.object(email_sender, "get_gmail_credentials")
def test_send_email_success(
    mock_credentials,
    mock_smtp,
):
    mock_credentials.return_value = (
        "sender@example.com",
        "fake-app-password",
    )

    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = email_sender.send_email(
        "recipient@example.com",
        "Test Subject",
        "Test Body",
    )

    assert result is True
    mock_server.login.assert_called_once_with(
        "sender@example.com",
        "fake-app-password",
    )
    mock_server.send_message.assert_called_once()

    sent_message = mock_server.send_message.call_args.args[0]

    assert sent_message["To"] == "recipient@example.com"
    assert sent_message["Subject"] == "Test Subject"
    assert sent_message.get_content().strip() == "Test Body"


@patch.object(email_sender.smtplib, "SMTP")
@patch.object(email_sender, "get_gmail_credentials")
def test_send_email_handles_smtp_failure(
    mock_credentials,
    mock_smtp,
):
    mock_credentials.return_value = (
        "sender@example.com",
        "fake-app-password",
    )

    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPException(
        "Simulated SMTP failure"
    )
    mock_smtp.return_value.__enter__.return_value = mock_server

    result = email_sender.send_email(
        "recipient@example.com",
        "Test Subject",
        "Test Body",
    )

    assert result is False