const profileKey = "sprakverkstan-profile";
const progressKey = "sprakverkstan-progress";

export function createAccountController({ progress, render, renderReview, onSessionChange }) {
  const elements = {
    toggle: document.getElementById("profileToggle"),
    panel: document.getElementById("profilePanel"),
    backdrop: document.getElementById("profileBackdrop"),
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
    modeHint: document.getElementById("profileModeHint"),
    submit: document.querySelector("#profileForm [type='submit']"),
  };

  let profile = readStoredProfile();
  let mode = "register";
  let syncTimer;
  let sessionAuthenticated = false;

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
    elements.title.textContent = signedIn ? "Your profile" : mode === "register" ? "Create your free account" : "Welcome back";
    elements.userName.textContent = signedIn ? profile.name : "Learner";
    elements.userEmail.textContent = signedIn ? profile.email : "No email saved";
    elements.toggle.textContent = signedIn ? `Profile · ${profile.name}` : "Sign in / Join free";
    elements.name.value = profile.name || "";
    elements.email.value = profile.email || "";
    elements.name.required = mode === "register";
    elements.nameField.hidden = mode === "login";
    elements.password.autocomplete = mode === "register" ? "new-password" : "current-password";
    elements.submit.textContent = mode === "register" ? "Create free account" : "Sign in to your account";
    elements.password.minLength = mode === "register" ? 8 : 0;
    elements.password.placeholder = mode === "register" ? "At least 8 characters" : "Your password";
    elements.modeHint.textContent = mode === "register" ? "Already learning with us?" : "New to Språkverkstan?";
    elements.modeToggle.textContent = mode === "register"
      ? "Sign in"
      : "Create a free account";
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
      sessionAuthenticated = false;
      if (profile.isLoggedIn) {
        profile = { isLoggedIn: false, name: "", email: "" };
        saveProfile();
      }
      await onSessionChange?.(false);
      return;
    }
    if (!response.ok) throw new Error("Could not load the account profile.");

    const { user } = await response.json();
    if (!user) return;
    sessionAuthenticated = true;
    profile = { isLoggedIn: true, name: user.name, email: user.email };
    saveProfile();
    await onSessionChange?.(true);

    let progressResponse;
    try {
      progressResponse = await fetch("/api/progress");
    } catch (error) {
      console.warn("Could not load account progress", error);
      return;
    }
    if (!progressResponse.ok) {
      console.warn("Could not load account progress", progressResponse.status);
      return;
    }
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
    elements.backdrop.hidden = !open;
    elements.toggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("profile-open", open);
    if (open) {
      (mode === "register" ? elements.name : elements.email).focus();
    } else {
      elements.toggle.focus();
    }
  }

  elements.toggle.addEventListener("click", () => setPanel(elements.panel.hidden));
  elements.close.addEventListener("click", () => setPanel(false));
  elements.backdrop.addEventListener("click", () => setPanel(false));
  elements.panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setPanel(false);
  });
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
      elements.submit.disabled = true;
      elements.submit.textContent = mode === "register" ? "Creating your account…" : "Signing you in…";
      const response = await fetch(mode === "register" ? "/api/register" : "/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "register" ? { name, email, password } : { email, password }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Could not authenticate.");

      profile = { isLoggedIn: true, name: result.user.name, email: result.user.email };
      sessionAuthenticated = true;
      elements.password.value = "";
      elements.status.textContent = `Welcome, ${profile.name}! Your account is saved in the database.`;
      saveProfile();
      await refreshProfile();
    } catch (error) {
      elements.status.textContent = error.message || "Could not save the profile.";
    } finally {
      elements.submit.disabled = false;
      renderProfile();
    }
  });

  elements.logout.addEventListener("click", async () => {
    try {
      const response = await fetch("/api/logout", { method: "POST" });
      if (!response.ok) throw new Error("The server could not end this session.");
    } catch (error) {
      elements.status.textContent = error.message || "Could not log out from backend.";
      return;
    }
    profile = { isLoggedIn: false, name: "", email: "" };
    sessionAuthenticated = false;
    mode = "login";
    elements.status.textContent = "You have signed out.";
    saveProfile();
    await onSessionChange?.(false);
  });

  async function initialize() {
    renderProfile();
    try {
      await refreshProfile();
    } catch (error) {
      sessionAuthenticated = false;
      profile = { isLoggedIn: false, name: "", email: "" };
      saveProfile();
      console.warn("Profile sync skipped", error);
      await onSessionChange?.(false);
    }
  }

  function promptLogin(message = "Sign in or create a free account to unlock all learning activities.") {
    if (sessionAuthenticated) return;
    mode = "login";
    renderProfile();
    elements.status.textContent = message;
    setPanel(true);
  }

  return {
    initialize,
    isLoggedIn: () => sessionAuthenticated,
    promptLogin,
    scheduleProgressSync,
  };
}