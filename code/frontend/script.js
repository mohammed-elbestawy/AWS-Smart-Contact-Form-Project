const API_URL = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod";

const form = document.getElementById("contact-form");
const submitBtn = document.getElementById("submit-btn");
const statusBox = document.getElementById("status");

function showStatus(message, type) {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showStatus("", "");

  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    subject: form.subject.value.trim(),
    message: form.message.value.trim(),
  };

  if (Object.values(payload).some((v) => !v)) {
    showStatus("Please fill in all fields.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Sending...";

  try {
    const res = await fetch(`${API_URL}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    showStatus(data.message || "Message sent successfully!", "success");
    form.reset();
  } catch (err) {
    showStatus(err.message || "Failed to send message. Please try again.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Send Message";
  }
});
