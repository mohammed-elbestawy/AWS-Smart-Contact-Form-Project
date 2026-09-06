const API_URL   = "https://5f2icwc8ud.execute-api.eu-north-1.amazonaws.com/prod";
const POOL_DATA = {
  UserPoolId: "eu-north-1_Vqyw75Hhf",
  ClientId:   "4hcb3fssvpgjepf5bpp97579cn",
};

const userPool = new AmazonCognitoIdentity.CognitoUserPool(POOL_DATA);

const loginForm      = document.getElementById("login-form");
const loginCard      = document.getElementById("login-card");
const dashboardCard  = document.getElementById("dashboard-card");
const loginStatus    = document.getElementById("login-status");
const loginBtn       = document.getElementById("login-btn");
const logoutBtn      = document.getElementById("logout-btn");
const messagesTable  = document.getElementById("messages-table");
const msgCount       = document.getElementById("msg-count");

function showLoginStatus(message, type) {
  loginStatus.textContent = message;
  loginStatus.className = `status ${type}`;
}

loginForm.addEventListener("submit", (e) => {
  e.preventDefault();
  showLoginStatus("", "");
  loginBtn.disabled = true;
  loginBtn.textContent = "Signing in...";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  const authDetails = new AmazonCognitoIdentity.AuthenticationDetails({
    Username: username,
    Password: password,
  });

  const cognitoUser = new AmazonCognitoIdentity.CognitoUser({
    Username: username,
    Pool: userPool,
  });

  cognitoUser.authenticateUser(authDetails, {
    onSuccess: (session) => {
      const idToken = session.getIdToken().getJwtToken();
      sessionStorage.setItem("idToken", idToken);
      showDashboard(idToken);
    },
    onFailure: (err) => {
      showLoginStatus(err.message || "Login failed.", "error");
      loginBtn.disabled = false;
      loginBtn.textContent = "Sign In";
    },
  });
});

logoutBtn.addEventListener("click", () => {
  sessionStorage.removeItem("idToken");
  dashboardCard.style.display = "none";
  loginCard.style.display = "block";
  loginBtn.disabled = false;
  loginBtn.textContent = "Sign In";
});

async function showDashboard(idToken) {
  loginCard.style.display = "none";
  dashboardCard.style.display = "block";

  try {
    const res = await fetch(`${API_URL}/messages`, {
      headers: { Authorization: idToken },
    });

    if (!res.ok) throw new Error("Failed to load messages.");

    const data = await res.json();
    msgCount.textContent = data.count;
    renderMessages(data.messages);
  } catch (err) {
    messagesTable.textContent = err.message;
  }
}

function renderMessages(messages) {
  if (!messages.length) {
    messagesTable.innerHTML = "<p>No messages yet.</p>";
    return;
  }

  const rows = messages.map((m) => `
    <tr class="${m.is_spam ? "spam-row" : ""}">
      <td>${escapeHtml(m.name)}</td>
      <td>${escapeHtml(m.email)}</td>
      <td>${escapeHtml(m.subject)}</td>
      <td>${escapeHtml(m.message)}</td>
      <td>${escapeHtml(m.sentiment || "-")}</td>
      <td>${m.is_spam ? "🚩 Spam" : "✅ Clean"}</td>
    </tr>
  `).join("");

  messagesTable.innerHTML = `
    <table>
      <thead>
        <tr><th>Name</th><th>Email</th><th>Subject</th><th>Message</th><th>Sentiment</th><th>Status</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// Restore session on page reload, if a token is still cached
const cachedToken = sessionStorage.getItem("idToken");
if (cachedToken) {
  showDashboard(cachedToken);
}
