const API_URL = "http://127.0.0.1:8000";

let currentDraftId = null;
let busy = false;
let approvedSnapshot = null;


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


function getCurrentEmail() {
    return {
        recipient: document.getElementById("recipient").value.trim(),
        subject: document.getElementById("subject").value.trim(),
        body: document.getElementById("body").value.trim()
    };
}


function getEmailSnapshot(email) {
    return JSON.stringify(email);
}


function invalidateApproval(message = "Email changed. Please approve it again.") {
    approvedSnapshot = null;

    const sendBtn = document.getElementById("sendBtn");
    const sendStatus = document.getElementById("sendStatus");

    sendBtn.disabled = true;
    sendStatus.textContent = message;
}


function updateApprovalState() {
    if (!approvedSnapshot) {
        return;
    }

    const currentSnapshot = getEmailSnapshot(getCurrentEmail());

    if (currentSnapshot !== approvedSnapshot) {
        invalidateApproval();
    }
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
    approvedSnapshot = null;

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

        document.getElementById("approveBtn").disabled = false;
        document.getElementById("sendBtn").disabled = true;
        document.getElementById("sendStatus").textContent = "";

        draftSection.hidden = false;

        status.textContent =
            "Email generated. Review and edit it before approving.";

    } catch (error) {
        status.textContent = `Error: ${error.message}`;
    } finally {
        busy = false;
        generateBtn.disabled = false;
    }
}


async function approveEmail() {
    if (busy) return;

    const sendStatus = document.getElementById("sendStatus");
    const approveBtn = document.getElementById("approveBtn");
    const email = getCurrentEmail();

    if (!currentDraftId) {
        sendStatus.textContent = "Please generate a new draft first.";
        return;
    }

    if (!email.recipient || !email.subject || !email.body) {
        sendStatus.textContent =
            "Recipient, subject, and body are required.";
        return;
    }

    const recipientInput = document.getElementById("recipient");

    if (!recipientInput.checkValidity()) {
        sendStatus.textContent = "Please enter a valid recipient email address.";
        recipientInput.reportValidity();
        return;
    }

    const confirmed = window.confirm(
        `Approve this exact email?\n\n` +
        `To: ${email.recipient}\n` +
        `Subject: ${email.subject}\n\n` +
        `Review the complete email body before approving.`
    );

    if (!confirmed) {
        sendStatus.textContent = "Approval cancelled.";
        return;
    }

    busy = true;
    approveBtn.disabled = true;
    document.getElementById("sendBtn").disabled = true;
    sendStatus.textContent = "Saving and approving your draft...";

    try {
        // Save the exact content the user reviewed.
        await apiRequest(`/api/drafts/${currentDraftId}/edit`, {
            method: "POST",
            body: JSON.stringify(email)
        });

        // Record approval for the saved version.
        const result = await apiRequest(
            `/api/drafts/${currentDraftId}/approve`,
            {
                method: "POST",
                body: JSON.stringify({
                    confirmation: "APPROVE"
                })
            }
        );

        // Enable sending only if the content is still unchanged.
        approvedSnapshot = getEmailSnapshot(getCurrentEmail());

        sendStatus.textContent =
            `${result.message} Review complete. You can now send this email.`;

        document.getElementById("sendBtn").disabled = false;

    } catch (error) {
        approvedSnapshot = null;
        document.getElementById("sendBtn").disabled = true;
        sendStatus.textContent = `Error: ${error.message}`;

    } finally {
        busy = false;
        approveBtn.disabled = false;
    }
}


async function sendEmail() {
    if (busy) return;

    const sendStatus = document.getElementById("sendStatus");
    const sendBtn = document.getElementById("sendBtn");
    const email = getCurrentEmail();

    if (!currentDraftId) {
        sendStatus.textContent = "Please generate a new draft first.";
        return;
    }

    if (!approvedSnapshot ||
        getEmailSnapshot(email) !== approvedSnapshot) {
        invalidateApproval(
            "Email is not approved or has changed. Please approve it again."
        );
        return;
    }

    const confirmed = window.confirm(
        `Send the approved email now?\n\n` +
        `To: ${email.recipient}\n` +
        `Subject: ${email.subject}\n\n` +
        `This action sends a real email.`
    );

    if (!confirmed) {
        sendStatus.textContent = "Sending cancelled.";
        return;
    }

    busy = true;
    sendBtn.disabled = true;
    document.getElementById("approveBtn").disabled = true;

    sendStatus.textContent = "Sending email...";

    try {
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
        approvedSnapshot = null;

    } catch (error) {
        sendStatus.textContent = `Error: ${error.message}`;

        // Do not automatically retry. If the result is uncertain,
        // check the SMTP logs before attempting another send.

    } finally {
        busy = false;

        // A failed request does not automatically restore approval.
        sendBtn.disabled = true;
        document.getElementById("approveBtn").disabled = false;
    }
}


function rejectEmail() {
    if (busy) return;

    currentDraftId = null;
    approvedSnapshot = null;

    document.getElementById("draftSection").hidden = true;
    document.getElementById("instructions").value = "";
    document.getElementById("status").textContent =
        "Draft rejected. No email was sent.";
    document.getElementById("sendStatus").textContent = "";
}


["recipient", "subject", "body"].forEach((id) => {
    document.getElementById(id).addEventListener(
        "input",
        updateApprovalState
    );
});