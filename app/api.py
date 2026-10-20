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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# In-memory draft storage for this local prototype.
drafts = {}
drafts_lock = Lock()


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