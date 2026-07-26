async function getCsrfToken() {
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to initialize security token");
  const data = await response.json();
  return data.csrf_token;
}

async function authFetch(url, options = {}) {
  const csrfToken = await getCsrfToken();
  const headers = {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrfToken,
    ...(options.headers || {}),
  };
  return fetch(url, {
    ...options,
    credentials: "include",
    cache: "no-store",
    headers,
  });
}

function showError(el, message) {
  el.textContent = message;
  el.classList.add("visible");
}

function hideError(el) {
  el.textContent = "";
  el.classList.remove("visible");
}

async function loadOAuthProviders(buttonEl) {
  try {
    const response = await fetch("/api/v1/auth/oauth/providers", { cache: "no-store" });
    const data = await response.json();
    const providers = data.providers || [];
    if (!providers.includes("google")) {
      buttonEl.style.display = "none";
      return;
    }
    buttonEl.href = "/api/v1/auth/oauth/google/start";
  } catch {
    buttonEl.style.display = "none";
  }
}
