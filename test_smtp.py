from app.email_sender import test_smtp_connection


if __name__ == "__main__":
    print("Testing Gmail SMTP connection...")

    success = test_smtp_connection()

    if success:
        print("Test passed. No email was sent.")
    else:
        print("Test failed. No email was sent.")