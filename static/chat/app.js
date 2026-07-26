const STORAGE_SESSION_KEY = "llm_chat_session_id";
const STORAGE_DOCS_PREFIX = "llm_chat_docs_";
/** @deprecated legacy key — cleared on every load */
const LEGACY_TOKEN_KEY = "llm_chat_token";

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const questionEl = document.getElementById("question");
const sendBtn = document.getElementById("send-btn");
const sessionIdEl = document.getElementById("session-id");
const useMemoryEl = document.getElementById("use-memory");
const useRagEl = document.getElementById("use-rag");
const useStreamEl = document.getElementById("use-stream");
const apiStatusEl = document.getElementById("api-status");
const authStatusEl = document.getElementById("auth-status");
const newChatBtn = document.getElementById("new-chat-btn");
const regenSessionBtn = document.getElementById("regen-session-btn");
const clearDocsBtn = document.getElementById("clear-docs-btn");
const attachBtn = document.getElementById("attach-btn");
const fileInput = document.getElementById("file-input");
const uploadedDocsEl = document.getElementById("uploaded-docs");
const urlInput = document.getElementById("url-input");
const urlIngestBtn = document.getElementById("url-ingest-btn");
const logoutBtn = document.getElementById("logout-btn");
const userEmailEl = document.getElementById("user-email");

/** @type {{ filename: string; document_id: string; chunks: number }[]} */
let uploadedDocuments = [];

let sessionId = localStorage.getItem(STORAGE_SESSION_KEY) || crypto.randomUUID();
let isSending = false;
let currentUser = null;
let csrfToken = "";

localStorage.removeItem(LEGACY_TOKEN_KEY);
sessionIdEl.value = sessionId;
loadSessionDocuments();

function docsStorageKey() {
  return `${STORAGE_DOCS_PREFIX}${sessionId}`;
}

function loadSessionDocuments() {
  try {
    uploadedDocuments = JSON.parse(localStorage.getItem(docsStorageKey()) || "[]");
  } catch {
    uploadedDocuments = [];
  }
  renderUploadedDocs();
  if (uploadedDocuments.length > 0) {
    useRagEl.checked = true;
  }
}

function saveSessionDocuments() {
  localStorage.setItem(docsStorageKey(), JSON.stringify(uploadedDocuments));
}

function buildChatPayload(question) {
  const hasSessionDocs = uploadedDocuments.length > 0;
  return {
    question,
    session_id: sessionId,
    use_memory: useMemoryEl.checked,
    use_rag: useRagEl.checked || hasSessionDocs,
    collection: "documents",
    metadata_filter: hasSessionDocs ? { session_id: sessionId } : {},
  };
}

function setBadge(el, text, ok) {
  el.textContent = text;
  el.classList.remove("ok", "error");
  if (ok === true) el.classList.add("ok");
  if (ok === false) el.classList.add("error");
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderMarkdown(text) {
  const escaped = escapeHtml(text);
  const withBold = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  const paragraphs = withBold.split(/\n{2,}/).map((block) => {
    if (block.includes("\n* ") || block.startsWith("* ")) {
      const items = block
        .split("\n")
        .map((line) => line.replace(/^\*\s+/, "").trim())
        .filter(Boolean)
        .map((item) => `<li>${item}</li>`)
        .join("");
      return `<ul>${items}</ul>`;
    }
    return `<p>${block.replaceAll("\n", "<br />")}</p>`;
  });
  return paragraphs.join("");
}

function createMessage(role, html, extra = "") {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="avatar">${role === "user" ? "You" : "AI"}</div>
    <div class="bubble">
      ${html}
      ${extra}
    </div>
  `;
  messagesEl.appendChild(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return article;
}

function buildMeta(response) {
  const chips = [];
  if (response.cached) chips.push('<span class="chip cached">cached</span>');
  if (response.total_tokens) chips.push(`<span class="chip">${response.total_tokens} tokens</span>`);
  if (typeof response.cost_usd === "number") {
    chips.push(`<span class="chip">$${response.cost_usd.toFixed(6)}</span>`);
  }
  return chips.length ? `<div class="meta">${chips.join("")}</div>` : "";
}

function buildSources(sources) {
  if (!sources?.length) return "";
  const items = sources
    .map((source) => {
      const label = source.metadata?.filename || source.id || "source";
      const preview = (source.content || "").slice(0, 120);
      return `<div class="source-item"><strong>${escapeHtml(label)}</strong> — ${escapeHtml(preview)}</div>`;
    })
    .join("");
  return `<div class="sources"><h3>Sources</h3>${items}</div>`;
}

async function ensureCsrf() {
  if (csrfToken) return csrfToken;
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to obtain CSRF token");
  const data = await response.json();
  csrfToken = data.csrf_token;
  return csrfToken;
}

async function ensureAuthenticated() {
  setBadge(authStatusEl, "checking…", null);
  const response = await fetch("/api/v1/auth/me", {
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    window.location.replace(`/auth/login.html?next=${encodeURIComponent("/chat/")}`);
    throw new Error("Authentication required");
  }
  if (!response.ok) throw new Error("Failed to resolve session");
  currentUser = await response.json();
  setBadge(authStatusEl, "authenticated", true);
  if (userEmailEl) {
    userEmailEl.textContent = currentUser.email || currentUser.id || "signed in";
  }
  await ensureCsrf();
  return currentUser;
}

async function authorizedFetch(url, options = {}) {
  const headers = {
    ...(options.headers || {}),
    "Cache-Control": "no-cache",
  };
  if (options.method && options.method.toUpperCase() !== "GET") {
    headers["X-CSRF-Token"] = await ensureCsrf();
  }

  const response = await fetch(url, {
    ...options,
    credentials: "include",
    cache: "no-store",
    headers,
  });

  if (response.status === 401) {
    window.location.replace(`/auth/login.html?next=${encodeURIComponent("/chat/")}`);
    throw new Error("Authentication required");
  }

  return response;
}

async function checkHealth() {
  try {
    const response = await fetch("/ready", { cache: "no-store" });
    const data = await response.json();
    const ok = data.status === "READY" || data.status === "DEGRADED";
    setBadge(apiStatusEl, ok ? data.status.toLowerCase() : "down", ok);
  } catch {
    setBadge(apiStatusEl, "offline", false);
  }
}

async function sendNonStreaming(payload) {
  const response = await authorizedFetch("/api/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.detail || "Chat request failed");
  }
  return data;
}

async function sendStreaming(payload, bubbleEl) {
  const response = await authorizedFetch("/api/v1/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.message || data.detail || "Stream request failed");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let content = "";
  let sources = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payloadText = line.slice(5).trim();
      if (payloadText === "[DONE]") continue;
      try {
        const event = JSON.parse(payloadText);
        if (event.type === "token") {
          content += event.content || "";
          bubbleEl.innerHTML = renderMarkdown(content);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (event.type === "sources") {
          sources = event.sources || [];
        } else if (event.content) {
          content += event.content || "";
          bubbleEl.innerHTML = renderMarkdown(content);
        }
      } catch {
        // ignore malformed chunks
      }
    }
  }

  return { content, sources };
}

async function handleSubmit(event) {
  event.preventDefault();
  if (isSending) return;

  const question = questionEl.value.trim();
  if (!question) return;

  isSending = true;
  sendBtn.disabled = true;
  createMessage("user", `<p>${escapeHtml(question)}</p>`);
  questionEl.value = "";
  questionEl.style.height = "auto";

  const payload = buildChatPayload(question);

  const assistantArticle = createMessage(
    "assistant",
    '<div class="typing"><span></span><span></span><span></span></div>'
  );
  const bubbleEl = assistantArticle.querySelector(".bubble");

  try {
    if (useStreamEl.checked) {
      const { content, sources } = await sendStreaming(payload, bubbleEl);
      bubbleEl.innerHTML =
        renderMarkdown(content || "No response.") + buildSources(sources);
    } else {
      const data = await sendNonStreaming(payload);
      sessionId = data.session_id || sessionId;
      sessionIdEl.value = sessionId;
      localStorage.setItem(STORAGE_SESSION_KEY, sessionId);
      bubbleEl.innerHTML =
        renderMarkdown(data.answer || "No response.") + buildMeta(data) + buildSources(data.sources);
    }
  } catch (error) {
    bubbleEl.innerHTML = `<p>${escapeHtml(error.message)}</p><div class="meta"><span class="chip error">error</span></div>`;
    setBadge(authStatusEl, "auth failed", false);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    questionEl.focus();
  }
}

function renderUploadedDocs() {
  uploadedDocsEl.innerHTML = uploadedDocuments
    .map(
      (doc) =>
        `<li title="${escapeHtml(doc.document_id)}">${escapeHtml(doc.filename)} · ${doc.chunks} chunks</li>`
    )
    .join("");
}

function addSystemMessage(text) {
  createMessage("assistant", `<p>${escapeHtml(text)}</p>`);
}

async function ingestFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authorizedFetch(
    `/api/v1/chat/upload?session_id=${encodeURIComponent(sessionId)}&collection=documents`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.detail || "Upload failed");
  }

  uploadedDocuments.unshift({
    filename: data.filename || file.name,
    document_id: data.document_id,
    chunks: data.chunks_indexed,
  });
  renderUploadedDocs();
  saveSessionDocuments();
  useRagEl.checked = true;
  addSystemMessage(
    `Document indexed for this chat (${data.chunks_indexed} chunks). Ask questions about "${data.filename}" — answers use only your uploaded files.`
  );
  return data;
}

async function ingestUrl(url) {
  const response = await authorizedFetch("/api/v1/chat/upload-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, session_id: sessionId, collection: "documents" }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.detail || "URL ingest failed");
  }

  uploadedDocuments.unshift({
    filename: data.filename || url,
    document_id: data.document_id,
    chunks: data.chunks_indexed,
  });
  renderUploadedDocs();
  saveSessionDocuments();
  useRagEl.checked = true;
  urlInput.value = "";
  addSystemMessage(
    `Indexed URL (${data.chunks_indexed} chunks, ${data.source_type}). RAG is now enabled.`
  );
  return data;
}

async function handleFileSelected(event) {
  const file = event.target.files?.[0];
  fileInput.value = "";
  if (!file) return;

  attachBtn.disabled = true;
  try {
    await ingestFile(file);
  } catch (error) {
    addSystemMessage(`Upload error: ${error.message}`);
  } finally {
    attachBtn.disabled = false;
  }
}

async function handleUrlIngest() {
  const url = urlInput.value.trim();
  if (!url) return;

  urlIngestBtn.disabled = true;
  try {
    await ingestUrl(url);
  } catch (error) {
    addSystemMessage(`URL ingest: ${error.message}`);
  } finally {
    urlIngestBtn.disabled = false;
  }
}

async function deleteSessionDocuments(targetSessionId = sessionId) {
  if (!targetSessionId) return { documents_deleted: 0, chunks_deleted: 0 };
  const response = await authorizedFetch(
    `/api/v1/chat/session/${encodeURIComponent(targetSessionId)}/documents?collection=documents`,
    { method: "DELETE" }
  );
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || data.detail || "Failed to delete session documents");
  }
  return data;
}

async function clearUploadedDocuments() {
  if (uploadedDocuments.length === 0) return;
  clearDocsBtn.disabled = true;
  try {
    const result = await deleteSessionDocuments(sessionId);
    uploadedDocuments = [];
    saveSessionDocuments();
    renderUploadedDocs();
    addSystemMessage(
      `Removed ${result.documents_deleted} document(s) and ${result.chunks_deleted} chunk(s) from Qdrant and Postgres.`
    );
  } catch (error) {
    addSystemMessage(`Could not clear uploads: ${error.message}`);
  } finally {
    clearDocsBtn.disabled = false;
  }
}

function resetConversation(keepSession) {
  messagesEl.innerHTML = `
    <article class="message assistant welcome">
      <div class="avatar">AI</div>
      <div class="bubble">
        <p>Upload a document with the + button, then ask questions about it. Answers use only files uploaded in this chat session.</p>
      </div>
    </article>
  `;
  if (!keepSession) {
    const previousSessionId = sessionId;
    sessionId = crypto.randomUUID();
    sessionIdEl.value = sessionId;
    localStorage.setItem(STORAGE_SESSION_KEY, sessionId);
    uploadedDocuments = [];
    saveSessionDocuments();
    renderUploadedDocs();
    deleteSessionDocuments(previousSessionId).catch(() => {
      // Best-effort cleanup of ephemeral vectors/metadata for the old session.
    });
  }
}

function autoResizeTextarea() {
  questionEl.style.height = "auto";
  questionEl.style.height = `${Math.min(questionEl.scrollHeight, 180)}px`;
}

newChatBtn.addEventListener("click", () => resetConversation(true));
regenSessionBtn.addEventListener("click", () => resetConversation(false));
clearDocsBtn.addEventListener("click", clearUploadedDocuments);
attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", handleFileSelected);
urlIngestBtn.addEventListener("click", handleUrlIngest);
formEl.addEventListener("submit", handleSubmit);
questionEl.addEventListener("input", autoResizeTextarea);
questionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formEl.requestSubmit();
  }
});

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      await authorizedFetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Still send the user to login.
    }
    window.location.replace("/auth/login.html");
  });
}

checkHealth();
ensureAuthenticated().catch(() => setBadge(authStatusEl, "auth failed", false));
