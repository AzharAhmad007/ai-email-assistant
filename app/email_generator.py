import json

import ollama

MODEL_NAME = "qwen3:4b"


def generate_email(instructions: str) -> dict:
    """
    Generate a structured email draft.

    This function generates content only.
    It does not send emails.
    """

    response = ollama.chat(
        model=MODEL_NAME,
        format="json",
        messages=[
            {
                "role": "system",
                "content": """
You are a professional email-writing assistant.

Generate an email based on the user's instructions.

Return a JSON object with exactly these three fields:
{
    "recipient": "recipient email address",
    "subject": "email subject",
    "body": "email body"
}

Rules:
1. Follow the user's instructions.
2. Keep the email professional and concise.
3. Do not invent a recipient's email address.
4. If the user has not provided an email address, use an empty string for recipient.
5. Do not include explanations outside the JSON object.
6. Never claim that the email has been sent.
""",
            },
            {
                "role": "user",
                "content": instructions,
            },
        ],
    )

    email_data = json.loads(response.message.content)

    return {
        "recipient": email_data.get("recipient", ""),
        "subject": email_data.get("subject", ""),
        "body": email_data.get("body", ""),
    }