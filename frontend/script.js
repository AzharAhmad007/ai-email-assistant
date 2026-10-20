const API_URL = "http://127.0.0.1:8000";

let currentDraftId = null;
let busy = false;


async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.detail || `Request failed with status ${response.status}`
        );
    }

    return data;
}


async function generateEmail() {
    if (busy) return;

    const instructions = document
        .getElementById("instructions")
        .value.trim();

    const status = document.getElementById("status");
    const generateBtn = document.getElementById("generateBtn");
    const draftSection = document.getElementById("draftSection");

    if (!instructions) {
        status.textContent = "Please describe the email you want to write.";
        return;
    }

    busy = true;
    generateBtn.disabled = true;
    draftSection.hidden = true;
    currentDraftId = null;

    status.textContent = "Generating your email...";

    try {
        const data = await apiRequest("/api/generate-email", {
            method: "POST",
            body: JSON.stringify({ instructions })
        });

        currentDraftId = data.draft_id;

        document.getElementById("recipient").value =
            data.recipient || "";

        document.getElementById("subject").value =
            data.subject || "";

        document.getElementById("body").value =
            data.body || "";

        document.getElementById("sendStatus").textContent = "";
        draftSection.hidden = false;

        status.textContent =
            "Email generated. Review and edit it before sending.";

    } catch (error) {
        status.textContent = `Error: ${error.message}`;
    } finally {
        busy = false;
        generateBtn.disabled = false;
    }
}


async function sendEmail() {
    if (busy) return;

    if (!currentDraftId) {
        document.getElementById("sendStatus").textContent =
            "Please generate a new email draft first.";
        return;
    }

    const recipient = document.getElementById("recipient").value.trim();
    const subject = document.getElementById("subject").value.trim();
    const body = document.getElementById("body").value.trim();

    if (!recipient || !subject || !body) {
        document.getElementById("sendStatus").textContent =
            "Recipient, subject, and body are required.";
        return;
    }

    const sendBtn = document.getElementById("sendBtn");
    const sendStatus = document.getElementById("sendStatus");

    const confirmed = window.confirm(
        `Send this email?\n\nTo: ${recipient}\nSubject: ${subject}`
    );

    if (!confirmed) {
        sendStatus.textContent = "Sending cancelled.";
        return;
    }

    busy = true;
    sendBtn.disabled = true;
    sendStatus.textContent = "Saving your edits...";

    try {
        // Save the exact version the user reviewed.
        await apiRequest(`/api/drafts/${currentDraftId}/edit`, {
            method: "POST",
            body: JSON.stringify({
                recipient,
                subject,
                body
            })
        });

        sendStatus.textContent = "Sending email...";

        // Explicit confirmation is required by the backend.
        const result = await apiRequest(
            `/api/drafts/${currentDraftId}/send`,
            {
                method: "POST",
                body: JSON.stringify({
                    confirmation: "SEND"
                })
            }
        );

        sendStatus.textContent = result.message;
        currentDraftId = null;

    } catch (error) {
        sendStatus.textContent = `Error: ${error.message}`;

        // If sending might have started, don't automatically retry.
        // Generate a fresh draft only after checking the SMTP logs
        // if the outcome of the previous send is uncertain.

    } finally {
        busy = false;
        sendBtn.disabled = false;
    }
}


function rejectEmail() {
    if (busy) return;

    currentDraftId = null;

    document.getElementById("draftSection").hidden = true;
    document.getElementById("instructions").value = "";
    document.getElementById("status").textContent =
        "Draft rejected. No email was sent.";
    document.getElementById("sendStatus").textContent = "";
}