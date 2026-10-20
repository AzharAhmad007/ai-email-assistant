from getpass import getpass

from app.email_sender import send_email


def main():
    recipient = input(
        "Enter the recipient email address: "
    ).strip()

    subject = input(
        "Enter the email subject: "
    ).strip()

    print("Enter the email body.")
    print("Enter a line containing END to finish.")

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    body = "\n".join(lines)

    print("\n" + "=" * 50)
    print("FINAL EMAIL REVIEW")
    print("=" * 50)
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    print("-" * 50)
    print(body)
    print("=" * 50)

    confirmation = input(
        "\nType SEND to send this exact email: "
    ).strip()

    if confirmation != "SEND":
        print("Cancelled. No email was sent.")
        return

    send_email(
        recipient=recipient,
        subject=subject,
        body=body,
    )


if __name__ == "__main__":
    main()