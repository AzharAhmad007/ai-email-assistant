from app.email_generator import generate_email
from app.email_sender import send_email


def display_email(email: dict) -> None:
    """Display the complete email draft."""

    print("\n" + "=" * 55)
    print("                  EMAIL DRAFT")
    print("=" * 55)

    print(f"To:      {email['recipient'] or '(not provided)'}")
    print(f"Subject: {email['subject'] or '(not provided)'}")

    print("-" * 55)
    print(email["body"])
    print("=" * 55)


def edit_email(email: dict) -> dict:
    """Allow the user to edit individual email fields."""

    updated_email = email.copy()

    print("\nWhat would you like to edit?")
    print("1. Recipient")
    print("2. Subject")
    print("3. Body")
    print("4. Cancel editing")

    choice = input("\nChoose an option (1-4): ").strip()

    if choice == "1":
        updated_email["recipient"] = input(
            "Enter recipient email address: "
        ).strip()

    elif choice == "2":
        updated_email["subject"] = input(
            "Enter the new subject: "
        ).strip()

    elif choice == "3":
        print("Enter the new email body.")
        print("Enter a line containing END to finish.")

        lines = []

        while True:
            line = input()

            if line.strip() == "END":
                break

            lines.append(line)

        updated_email["body"] = "\n".join(lines)

    elif choice == "4":
        print("Editing cancelled.")
        return email

    else:
        print("Invalid option.")
        return email

    return updated_email


def confirm_and_send(email: dict) -> None:
    """Require final confirmation before sending the email."""

    print("\nPlease review the final email before sending.")
    display_email(email)

    confirmation = input(
        "\nType SEND to send this exact email: "
    ).strip()

    if confirmation != "SEND":
        print("\nSending cancelled. No email was sent.")
        return

    try:
        success = send_email(
            recipient=email["recipient"],
            subject=email["subject"],
            body=email["body"],
        )

        if success:
            print("\nEmail sending process completed.")
        else:
            print(
                "\nThe email was not confirmed as sent. "
                "Check the error and your Gmail account."
            )

    except ValueError as exc:
        print(f"\nEmail validation failed: {exc}")
        print("No email was sent.")

    except Exception as exc:
        print(f"\nAn unexpected error occurred: {exc}")
        print(
            "Check your email account before retrying, "
            "as the delivery status may be uncertain."
        )


def main():
    print("=" * 55)
    print("                AI EMAIL ASSISTANT")
    print("=" * 55)

    instructions = input(
        "\nDescribe the email you want to write:\n> "
    ).strip()

    if not instructions:
        print("Please provide email instructions.")
        return

    print("\nGenerating your email...")

    try:
        email = generate_email(instructions)

    except Exception as exc:
        print(f"\nFailed to generate email: {exc}")
        return

    # Review loop: edits always return to the review screen.
    while True:
        display_email(email)

        print("\nChoose an action:")
        print("1. Approve and continue")
        print("2. Edit draft")
        print("3. Reject draft")

        choice = input("\nChoose an option (1/2/3): ").strip()

        if choice == "1":
            # Stop if any required field is missing.
            if not all(
                isinstance(email.get(field), str)
                and email[field].strip()
                for field in ("recipient", "subject", "body")
            ):
                print(
                    "\nRecipient, subject, and body are required. "
                    "Please edit the draft."
                )
                continue

            confirm_and_send(email)
            break

        elif choice == "2":
            updated_email = edit_email(email)

            if updated_email != email:
                email = updated_email
                print(
                    "\nDraft updated. Review the complete email "
                    "and approve it again."
                )
            else:
                print("\nDraft unchanged.")

        elif choice == "3":
            print("\nDraft rejected. No email was sent.")
            break

        else:
            print("\nInvalid option. Choose 1, 2, or 3.")


if __name__ == "__main__":
    main()