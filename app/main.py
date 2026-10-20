from app.email_generator import generate_email


def display_email(email: dict) -> None:
    """Display the email fields separately."""

    print("\n" + "=" * 50)
    print("              EMAIL DRAFT")
    print("=" * 50)

    print(f"To:      {email['recipient'] or '(not provided)'}")
    print(f"Subject: {email['subject']}")
    print("-" * 50)
    print(email["body"])
    print("=" * 50)


def edit_email(email: dict) -> dict:
    """Allow the user to edit individual email fields."""

    print("\nWhich field would you like to edit?")
    print("1. Recipient")
    print("2. Subject")
    print("3. Body")
    print("4. Cancel editing")

    choice = input("\nChoose an option (1-4): ").strip()

    updated_email = email.copy()

    if choice == "1":
        updated_email["recipient"] = input(
            "Enter recipient email address: "
        ).strip()

    elif choice == "2":
        updated_email["subject"] = input(
            "Enter the new subject: "
        ).strip()

    elif choice == "3":
        print("Enter the new body.")
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


def main():
    print("=" * 50)
    print("             AI EMAIL ASSISTANT")
    print("=" * 50)

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

    while True:
        display_email(email)

        print("\n1. Approve draft")
        print("2. Edit draft")
        print("3. Reject draft")

        choice = input("\nChoose an option (1/2/3): ").strip()

        if choice == "1":
            print("\nDraft approved.")
            print(
                "Sending is not implemented yet. "
                "No email has been sent."
            )
            break

        elif choice == "2":
            email = edit_email(email)

            print("\nDraft updated.")
            print(
                "Review the updated email carefully. "
                "You must approve it again."
            )

        elif choice == "3":
            print("\nDraft rejected. No email has been sent.")
            break

        else:
            print("\nInvalid option. Please choose 1, 2, or 3.")


if __name__ == "__main__":
    main()