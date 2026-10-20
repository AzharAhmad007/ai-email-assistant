import os
import smtplib
import ssl
import certifi

from dotenv import load_dotenv

from email.message import EmailMessage
from email.utils import parseaddr

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def get_gmail_credentials() -> tuple[str, str]:
    """Load Gmail credentials from environment variables."""

    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        raise ValueError(
            "Gmail credentials are missing. "
            "Check your .env file."
        )

    return gmail_address, gmail_app_password


def test_smtp_connection() -> bool:
    """Test Gmail SMTP authentication without sending an email."""

    gmail_address, gmail_app_password = get_gmail_credentials()

    try:
        context = ssl.create_default_context(
            cafile=certifi.where()
        )

        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT,
            timeout=20,
        ) as server:

            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            server.login(
                gmail_address,
                gmail_app_password,
            )

            print("Gmail SMTP authentication successful.")
            return True

    except smtplib.SMTPAuthenticationError:
        print(
            "Authentication failed. Check your Gmail address "
            "and App Password."
        )
        return False

    except (OSError, smtplib.SMTPException) as exc:
        print(f"SMTP connection failed: {exc}")
        return False
    
def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> bool:
    """
    Send an email through Gmail SMTP.

    This function should only be called after
    the user explicitly approves the final draft.
    """

    # Basic validation
    recipient = recipient.strip()
    subject = subject.strip()

    if not recipient or not subject or not body.strip():
        raise ValueError(
            "Recipient, subject, and body are required."
        )

    # Validate the recipient address
    parsed_name, parsed_address = parseaddr(recipient)

    if parsed_address != recipient or (
        parsed_address.count("@") != 1
        or "." not in parsed_address.rsplit("@", 1)[-1]
    ):
        raise ValueError("Invalid recipient email address.")

    gmail_address, gmail_app_password = get_gmail_credentials()

    # Construct the email
    message = EmailMessage()
    message["From"] = gmail_address
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    # Send through Gmail SMTP
    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    try:
        with smtplib.SMTP(
            SMTP_SERVER,
            SMTP_PORT,
            timeout=20,
        ) as server:

            server.ehlo()
            server.starttls(context=context)
            server.ehlo()

            server.login(
                gmail_address,
                gmail_app_password,
            )

            server.send_message(message)

        print(f"Email sent successfully to {recipient}.")
        return True

    except smtplib.SMTPAuthenticationError:
        print("Gmail authentication failed.")
        return False

    except (OSError, smtplib.SMTPException) as exc:
        print(f"Failed to send email: {exc}")
        return False