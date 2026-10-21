import hashlib
import json
import secrets
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from app.email_generator import generate_email
from app.email_sender import send_email

app = FastAPI(title="AI Email Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# In-memory draft storage for this local prototype.
drafts = {}
drafts_lock = Lock()

def calculate_draft_hash(draft: dict) -> str:
    """Create a fingerprint of the exact email content."""
    content = {
        "recipient": draft["recipient"],
        "subject": draft["subject"],
        "body": draft["body"],
    }

    serialized = json.dumps(
        content,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class EmailInstructions(BaseModel):
    instructions: str = Field(min_length=1, max_length=5000)


class EmailDetails(BaseModel):
    recipient: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class DraftUpdate(EmailDetails):
    pass


class SendConfirmation(BaseModel):
    confirmation: str


@app.get("/")
def home():
    return {"message": "AI Email Assistant API is running!"}


@app.post("/api/generate-email")
def create_email(request: EmailInstructions):
    try:
        email = generate_email(request.instructions)

        # Validate the generated fields before saving the draft.
        if not email.get("subject") or not email.get("body"):
            raise HTTPException(
                status_code=502,
                detail="The AI generated an incomplete email.",
            )

        draft_id = secrets.token_urlsafe(32)

        draft = {
            "recipient": email.get("recipient", ""),
            "subject": email["subject"],
            "body": email["body"],
            "status": "pending",
            "approved": False,
        }

        with drafts_lock:
            drafts[draft_id] = draft

        return {
            "draft_id": draft_id,
            "recipient": draft["recipient"],
            "subject": draft["subject"],
            "body": draft["body"],
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Email generation failed.",
        )

@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    with drafts_lock:
        draft = drafts.get(draft_id)

        if not draft:
            raise HTTPException(
                status_code=404,
                detail="Draft not found.",
            )

        return {
            "draft_id": draft_id,
            **draft,
        }

@app.post("/api/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    confirmation: SendConfirmation,
):
    if confirmation.confirmation != "APPROVE":
        raise HTTPException(
            status_code=400,
            detail="Explicit APPROVE confirmation is required.",
        )

    with drafts_lock:
        draft = drafts.get(draft_id)

        if not draft or draft["status"] != "pending":
            raise HTTPException(
                status_code=404,
                detail="Draft not found or no longer available for approval.",
            )

        if not draft.get("recipient"):
            raise HTTPException(
                status_code=400,
                detail="Please provide a recipient email address.",
            )

        draft["approved_content_hash"] = calculate_draft_hash(draft)
        draft["approved"] = True

    return {"message": "Draft approved successfully."}

@app.post("/api/drafts/{draft_id}/edit")
def edit_draft(draft_id: str, email: DraftUpdate):
    with drafts_lock:
        draft = drafts.get(draft_id)

        if not draft or draft["status"] != "pending":
            raise HTTPException(
                status_code=404,
                detail="Draft not found or no longer editable.",
            )

        # Replace the draft with the exact reviewed content.
        draft.update(email.model_dump())
        draft["status"] = "pending"
        draft["approved"] = False

    return {"message": "Draft updated successfully."}


@app.post("/api/drafts/{draft_id}/send")
def approve_and_send(
    draft_id: str,
    confirmation: SendConfirmation,
):
    if confirmation.confirmation != "SEND":
        raise HTTPException(
            status_code=400,
            detail="Explicit SEND confirmation is required.",
        )

    # Reserve the draft before sending to prevent simultaneous
    # requests from sending the same draft more than once.
    with drafts_lock:
        draft = drafts.get(draft_id)

        if not draft or draft["status"] != "pending":
            raise HTTPException(
                status_code=404,
                detail="Draft not found, already processed, or unavailable.",
            )

        if not draft.get("recipient"):
            raise HTTPException(
                status_code=400,
                detail="Please provide a recipient email address.",
            )

        # Verify that the user has approved this draft.
        if not draft.get("approved"):
            raise HTTPException(
                status_code=403,
                detail="The email must be approved before sending.",
            )

        # Verify that the email content has not changed since approval.
        current_hash = calculate_draft_hash(draft)

        if current_hash != draft.get("approved_content_hash"):
            draft["approved"] = False
            draft.pop("approved_content_hash", None)

            raise HTTPException(
                status_code=403,
                detail="The email changed after approval. Review and approve it again.",
            )

        # Reserve the draft to prevent simultaneous send attempts.
        draft["status"] = "sending"

        email_to_send = {
            "recipient": draft["recipient"],
            "subject": draft["subject"],
            "body": draft["body"],
        }

    try:
        success = send_email(
            recipient=email_to_send["recipient"],
            subject=email_to_send["subject"],
            body=email_to_send["body"],
        )

        with drafts_lock:
            if success:
                drafts[draft_id]["status"] = "sent"
            else:
                drafts[draft_id]["status"] = "failed"

        if not success:
            raise HTTPException(
                status_code=502,
                detail=(
                    "The email could not be confirmed as sent. "
                    "Check the SMTP logs before retrying."
                ),
            )

        return {"message": "Email accepted by the SMTP server."}

    except HTTPException:
        raise
    except Exception:
        # Avoid automatically retrying: the SMTP server might
        # have accepted the message before the error occurred.
        with drafts_lock:
            if draft_id in drafts:
                drafts[draft_id]["status"] = "uncertain"

        raise HTTPException(
            status_code=502,
            detail=(
                "The sending outcome is uncertain. "
                "Check SMTP logs before attempting another send."
            ),
        )