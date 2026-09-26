const profileKey = "sprakverkstan-profile";
const progressKey = "sprakverkstan-progress";

export function createAccountController({ progress, render, renderReview }) {
  const elements = {
    toggle: document.getElementById("profileToggle"),
    panel: document.getElementById("profilePanel"),
    form: document.getElementById("profileForm"),
    nameField: document.getElementById("profileNameField"),
    name: document.getElementById("profileNameInput"),
    email: document.getElementById("profileEmailInput"),
    password: document.getElementById("profilePasswordInput"),
    status: document.getElementById("profileStatus"),
    title: document.getElementById("profileTitle"),
    loggedIn: document.getElementById("profileLoggedIn"),
    userName: document.getElementById("profileUserName"),
    userEmail: document.getElementById("profileUserEmail"),
    close: document.getElementById("closeProfile"),
    logout: document.getElementById("logoutButton"),
    modeToggle: document.getElementById("profileModeToggle"),
  };

  let profile = readStoredProfile();
  let mode = "register";
  let syncTimer;

  function readStoredProfile() {
    try {
      return JSON.parse(localStorage.getItem(profileKey) || "null") || {
        isLoggedIn: false,
        name: "",
        email: "",
      };
    } catch {
      return { isLoggedIn: false, name: "", email: "" };
    }
  }

  function saveProfile() {
    localStorage.setItem(profileKey, JSON.stringify(profile));
    renderProfile();
  }

  function renderProfile() {
    const signedIn = profile.isLoggedIn && profile.name;
    elements.form.hidden = Boolean(signedIn);
    elements.loggedIn.hidden = !signedIn;
    elements.title.textContent = signedIn ? "Your profile" : mode === "register" ? "Create account" : "Sign in";
    elements.userName.textContent = signedIn ? profile.name : "Learner";
    elements.userEmail.textContent = signedIn ? profile.email : "No email saved";
    elements.toggle.textContent = signedIn ? `Profile · ${profile.name}` : "Profile";
    elements.name.value = profile.name || "";
    elements.email.value = profile.email || "";
    elements.name.required = mode === "register";
    elements.nameField.hidden = mode === "login";
    elements.password.autocomplete = mode === "register" ? "new-password" : "current-password";
    elements.form.querySelector('[type="submit"]').textContent = mode === "register" ? "Create account" : "Sign in";
    elements.modeToggle.textContent = mode === "register"
      ? "Already have an account? Sign in"
      : "New here? Create an account";
  }

  function scheduleProgressSync() {
    if (!profile.isLoggedIn) return;
    clearTimeout(syncTimer);
    syncTimer = setTimeout(syncProgress, 400);
  }

  async function syncProgress() {
    if (!profile.isLoggedIn) return;
    try {
      const response = await fetch("/api/progress", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(progress),
      });
      if (!response.ok) throw new Error("Progress sync failed.");
    } catch (error) {
      console.warn("Progress remains saved locally; backend sync failed", error);
    }
  }

  async function refreshProfile() {
    const response = await fetch("/api/me");
    if (response.status === 401) {
      if (profile.isLoggedIn) {
        profile = { isLoggedIn: false, name: "", email: "" };
        saveProfile();
      }
      return;
    }
    if (!response.ok) throw new Error("Could not load the account profile.");

    const { user } = await response.json();
    if (!user) return;
    profile = { isLoggedIn: true, name: user.name, email: user.email };
    saveProfile();

    const progressResponse = await fetch("/api/progress");
    if (!progressResponse.ok) return;
    const serverProgress = await progressResponse.json();
    for (const [key, value] of Object.entries(serverProgress)) {
      progress[key] = Array.isArray(value) && Array.isArray(progress[key])
        ? [...new Set([...value, ...progress[key]])]
        : value;
    }
    localStorage.setItem(progressKey, JSON.stringify(progress));
    renderReview();
    render();
    await syncProgress();
  }

  function setPanel(open) {
    elements.panel.hidden = !open;
    elements.toggle.setAttribute("aria-expanded", String(open));
  }

  elements.toggle.addEventListener("click", () => setPanel(elements.panel.hidden));
  elements.close.addEventListener("click", () => setPanel(false));
  elements.modeToggle.addEventListener("click", () => {
    mode = mode === "register" ? "login" : "register";
    elements.status.textContent = "";
    renderProfile();
  });

  elements.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = elements.name.value.trim();
    const email = elements.email.value.trim();
    const password = elements.password.value;

    try {
      const response = await fetch(mode === "register" ? "/api/register" : "/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "register" ? { name, email, password } : { email, password }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Could not authenticate.");

      profile = { isLoggedIn: true, name: result.user.name, email: result.user.email };
      elements.password.value = "";
      elements.status.textContent = `Welcome, ${profile.name}! Your account is saved in the database.`;
      saveProfile();
      await refreshProfile();
    } catch (error) {
      elements.status.textContent = error.message || "Could not save the profile.";
    }
  });

  elements.logout.addEventListener("click", async () => {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (error) {
      console.warn("Could not log out from backend", error);
    }
    profile = { isLoggedIn: false, name: "", email: "" };
    mode = "login";
    elements.status.textContent = "You have signed out.";
    saveProfile();
  });

  async function initialize() {
    renderProfile();
    if (!profile.isLoggedIn) return;
    try {
      await refreshProfile();
    } catch (error) {
      console.warn("Profile sync skipped", error);
    }
  }

  return { initialize, scheduleProgressSync };
}