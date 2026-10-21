import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("AI Email Assistant")

API_BASE_URL = "http://127.0.0.1:8000"


@mcp.tool()
async def generate_email(instructions: str) -> dict:
    """
    Generate an email draft using the AI Email Assistant.
    Returns the draft ID, recipient, subject, and body.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/generate-email",
            json={"instructions": instructions},
        )

        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_email_draft(draft_id: str) -> dict:
    """
    Retrieve an existing email draft using its draft ID.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_BASE_URL}/api/drafts/{draft_id}"
        )

        response.raise_for_status()
        return response.json()

@mcp.tool()
async def update_email_draft(
    draft_id: str,
    recipient: str,
    subject: str,
    body: str,
) -> dict:
    """
    Update an existing email draft's recipient, subject, and body.
    Only drafts that are still pending can be updated.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/drafts/{draft_id}/edit",
            json={
                "recipient": recipient,
                "subject": subject,
                "body": body,
            },
        )

        response.raise_for_status()
        return response.json()

@mcp.tool()
async def send_approved_email(
    draft_id: str,
    confirmation: str,
) -> dict:
    """
    Send an email draft only when the user has explicitly approved
    the exact draft by providing the required SEND confirmation.

    The draft must have a valid recipient and still be pending.
    """
    if confirmation != "SEND":
        raise ValueError(
            "Explicit user approval is required. "
            "The confirmation must be exactly 'SEND'."
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/drafts/{draft_id}/send",
            json={"confirmation": confirmation},
        )

        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")