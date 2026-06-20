import {
  buildMobileGuide,
  buildCopyText,
  detectClientPlatform,
  filterPrompts,
  normalizeLibraryPayload,
  parseStoredLibrary,
  resolveBoardEntries,
  resolveSelectedVersion,
  serializeLibrary,
  summarizeLibrary,
} from "./library.js";

window.addEventListener("error", (event) => {
  document.body.dataset.appError = event.message || "unknown-error";
});

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason;
  document.body.dataset.appError =
    reason instanceof Error ? reason.message : String(reason ?? "unhandled-rejection");
});

const STORAGE_KEYS = {
  library: "profiprompt-companion-library",
  ui: "profiprompt-companion-ui",
};

const state = {
  library: null,
  boardId: "all",
  promptId: null,
  versionId: "",
  query: "",
  copyMode: "all",
  includeMetadata: true,
};

const elements = {
  importFile: document.querySelector("#import-file"),
  importTrigger: document.querySelector("#import-trigger"),
  clearLibrary: document.querySelector("#clear-library"),
  searchInput: document.querySelector("#search-input"),
  copyMode: document.querySelector("#copy-mode"),
  includeMetadata: document.querySelector("#include-metadata"),
  copyButton: document.querySelector("#copy-button"),
  installApp: document.querySelector("#install-app"),
  mobileGuidePlatform: document.querySelector("#mobile-guide-platform"),
  mobileGuideInstall: document.querySelector("#mobile-guide-install"),
  mobileGuideImport: document.querySelector("#mobile-guide-import"),
  mobileGuideOffline: document.querySelector("#mobile-guide-offline"),
  mobileGuideCopy: document.querySelector("#mobile-guide-copy"),
  versionSelect: document.querySelector("#version-select"),
  libraryStatus: document.querySelector("#library-status"),
  statPrompts: document.querySelector("#stat-prompts"),
  statVersions: document.querySelector("#stat-versions"),
  statBoards: document.querySelector("#stat-boards"),
  statTags: document.querySelector("#stat-tags"),
  boardCount: document.querySelector("#board-count"),
  promptCount: document.querySelector("#prompt-count"),
  boardList: document.querySelector("#board-list"),
  promptList: document.querySelector("#prompt-list"),
  detailTitle: document.querySelector("#detail-title"),
  detailPurpose: document.querySelector("#detail-purpose"),
  detailMeta: document.querySelector("#detail-meta"),
  detailTextLabel: document.querySelector("#detail-text-label"),
  detailText: document.querySelector("#detail-text"),
  detailResult: document.querySelector("#detail-result"),
  copyFallback: document.querySelector("#copy-fallback"),
  copyFallbackText: document.querySelector("#copy-fallback-text"),
  copyFallbackSelect: document.querySelector("#copy-fallback-select"),
  copyFallbackClose: document.querySelector("#copy-fallback-close"),
  toast: document.querySelector("#toast"),
};

let deferredInstallPrompt = null;
let toastTimer = null;

bootstrap();

function bootstrap() {
  restoreState();
  bindEvents();
  registerServiceWorker();
  void maybeLoadLibraryFromQuery();
  render();
}

function bindEvents() {
  elements.importFile.addEventListener("change", onImportFileChange);
  elements.importTrigger.addEventListener("click", openImportPicker);
  elements.clearLibrary.addEventListener("click", clearLibrary);
  elements.searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    ensureSelection();
    persistUiState();
    render();
  });
  elements.copyMode.addEventListener("change", (event) => {
    state.copyMode = event.target.value;
    persistUiState();
  });
  elements.includeMetadata.addEventListener("change", (event) => {
    state.includeMetadata = event.target.checked;
    persistUiState();
  });
  elements.copyButton.addEventListener("click", copySelection);
  elements.versionSelect.addEventListener("change", (event) => {
    state.versionId = event.target.value;
    persistUiState();
    renderDetail();
  });
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    elements.installApp.hidden = false;
  });
  elements.installApp.addEventListener("click", async () => {
    if (!deferredInstallPrompt) {
      return;
    }
    const pendingPrompt = deferredInstallPrompt;
    deferredInstallPrompt = null;
    pendingPrompt.prompt();
    await pendingPrompt.userChoice;
    elements.installApp.hidden = true;
    renderQuickGuide();
  });
  elements.copyFallbackSelect.addEventListener("click", selectFallbackCopyText);
  elements.copyFallbackClose.addEventListener("click", closeCopyFallback);
}

function openImportPicker() {
  try {
    if (typeof elements.importFile.showPicker === "function") {
      elements.importFile.showPicker();
      return;
    }
  } catch {
    // Fall through to click() when showPicker() is unsupported or blocked.
  }
  elements.importFile.click();
}

async function onImportFileChange(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }
  try {
    const raw = await file.text();
    const payload = normalizeLibraryPayload(JSON.parse(raw));
    state.library = payload;
    state.boardId = "all";
    state.promptId = payload.prompts[0]?.id ?? null;
    state.versionId = "";
    try {
      localStorage.setItem(STORAGE_KEYS.library, serializeLibrary(payload));
    } catch {
      // QuotaExceededError in Safari Private Browsing oder bei vollem Speicher
    }
    persistUiState();
    ensureSelection();
    render();
    showToast(`Bibliothek geladen: ${payload.prompts.length} Prompts.`);
  } catch (error) {
    showToast(error instanceof Error ? error.message : "Import fehlgeschlagen.");
  } finally {
    event.target.value = "";
  }
}

async function maybeLoadLibraryFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const libraryPath = params.get("library");
  if (!libraryPath) {
    return;
  }
  try {
    const response = await fetch(libraryPath, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Demo-Bibliothek konnte nicht geladen werden (${response.status}).`);
    }
    const payload = normalizeLibraryPayload(await response.json());
    state.library = payload;
    state.boardId = "all";
    state.promptId = payload.prompts[0]?.id ?? null;
    state.versionId = "";
    try {
      localStorage.setItem(STORAGE_KEYS.library, serializeLibrary(payload));
    } catch {
      // QuotaExceededError in Safari Private Browsing oder bei vollem Speicher
    }
    persistUiState();
    ensureSelection();
    render();
    showToast("Demo-Bibliothek geladen.");
  } catch (error) {
    showToast(error instanceof Error ? error.message : "Demo-Bibliothek fehlgeschlagen.");
  }
}

function clearLibrary() {
  state.library = null;
  state.boardId = "all";
  state.promptId = null;
  state.versionId = "";
  try { localStorage.removeItem(STORAGE_KEYS.library); } catch { /* storage blocked */ }
  persistUiState();
  render();
  showToast("Lokale Bibliothek gelöscht.");
}

async function copySelection() {
  const prompt = getSelectedPrompt();
  if (!prompt) {
    return;
  }
  const version = resolveSelectedVersion(prompt, state.versionId);
  const text = buildCopyText(prompt, version, {
    mode: state.copyMode,
    includeMetadata: state.includeMetadata,
  });
  try {
    await navigator.clipboard.writeText(text);
    closeCopyFallback();
    showToast("Auswahl in die Zwischenablage kopiert.");
    return;
  } catch {
    if (fallbackCopy(text)) {
      closeCopyFallback();
      showToast("Auswahl in die Zwischenablage kopiert.");
      return;
    }
  }
  openCopyFallback(text);
  showToast("Zwischenablage blockiert. Bitte Text manuell kopieren.");
}

function fallbackCopy(text) {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "absolute";
  area.style.left = "-9999px";
  document.body.append(area);
  try {
    area.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}

function openCopyFallback(text) {
  elements.copyFallbackText.value = text;
  elements.copyFallback.hidden = false;
  selectFallbackCopyText();
}

function closeCopyFallback() {
  elements.copyFallback.hidden = true;
  elements.copyFallbackText.value = "";
}

function selectFallbackCopyText() {
  elements.copyFallbackText.focus();
  elements.copyFallbackText.select();
}

function restoreState() {
  let storedLibrary = null;
  let storedUi = null;
  try {
    storedLibrary = localStorage.getItem(STORAGE_KEYS.library);
    storedUi = localStorage.getItem(STORAGE_KEYS.ui);
  } catch {
    // localStorage blocked by security policy (Safari Private, sandboxed iframe)
  }

  try {
    state.library = parseStoredLibrary(storedLibrary);
  } catch {
    try { localStorage.removeItem(STORAGE_KEYS.library); } catch { /* storage blocked */ }
  }

  try {
    const ui = storedUi ? JSON.parse(storedUi) : {};
    state.boardId = typeof ui.boardId === "string" ? ui.boardId : "all";
    state.promptId = typeof ui.promptId === "string" ? ui.promptId : null;
    state.versionId = typeof ui.versionId === "string" ? ui.versionId : "";
    state.query = typeof ui.query === "string" ? ui.query : "";
    state.copyMode = typeof ui.copyMode === "string" ? ui.copyMode : "all";
    state.includeMetadata = ui.includeMetadata !== false;
  } catch {
    try { localStorage.removeItem(STORAGE_KEYS.ui); } catch { /* storage blocked */ }
  }

  elements.searchInput.value = state.query;
  elements.copyMode.value = state.copyMode;
  elements.includeMetadata.checked = state.includeMetadata;
  ensureSelection();
}

function persistUiState() {
  try {
    localStorage.setItem(
      STORAGE_KEYS.ui,
      JSON.stringify({
        boardId: state.boardId,
        promptId: state.promptId,
        versionId: state.versionId,
        query: state.query,
        copyMode: state.copyMode,
        includeMetadata: state.includeMetadata,
      }),
    );
  } catch {
    // QuotaExceededError in Safari Private Browsing oder bei vollem Speicher
  }
}

function ensureSelection() {
  if (!state.library) {
    state.promptId = null;
    state.versionId = "";
    return;
  }

  if (state.boardId !== "all" && !state.library.boards.some((board) => board.id === state.boardId)) {
    state.boardId = "all";
  }

  const prompts = getVisiblePrompts();
  if (!prompts.length) {
    state.promptId = null;
    state.versionId = "";
    return;
  }

  if (!prompts.some((prompt) => prompt.id === state.promptId)) {
    state.promptId = prompts[0].id;
    state.versionId = "";
  }

  const prompt = getSelectedPrompt();
  if (!prompt) {
    state.versionId = "";
    return;
  }
  if (state.versionId && !prompt.versions.some((version) => version.id === state.versionId)) {
    state.versionId = "";
  }
}

function getVisiblePrompts() {
  if (!state.library) {
    return [];
  }
  return filterPrompts(state.library, {
    query: state.query,
    boardId: state.boardId,
  });
}

function getSelectedPrompt() {
  return getVisiblePrompts().find((prompt) => prompt.id === state.promptId) ?? null;
}

function render() {
  renderStats();
  renderQuickGuide();
  renderBoards();
  renderPrompts();
  renderDetail();
}

function renderQuickGuide() {
  const guide = buildMobileGuide({
    userAgent: navigator.userAgent,
    hasInstallPrompt: Boolean(deferredInstallPrompt),
    hasLibrary: state.library != null,
  });
  const platform = detectClientPlatform(navigator.userAgent);
  elements.mobileGuidePlatform.textContent = guide.platformLabel;
  elements.mobileGuideInstall.textContent = guide.installText;
  elements.mobileGuideImport.textContent = guide.importText;
  elements.mobileGuideOffline.textContent = guide.offlineText;
  elements.mobileGuideCopy.textContent = guide.copyText;
  document.body.dataset.platform = platform;
}

function renderStats() {
  if (!state.library) {
    elements.libraryStatus.textContent = "Keine Bibliothek geladen";
    elements.statPrompts.textContent = "0";
    elements.statVersions.textContent = "0";
    elements.statBoards.textContent = "0";
    elements.statTags.textContent = "0";
    return;
  }

  const summary = summarizeLibrary(state.library);
  const exportedAt = state.library.app.exported_at
    ? new Date(state.library.app.exported_at).toLocaleString("de-DE")
    : "unbekannt";
  elements.libraryStatus.textContent = `${state.library.app.name} ${state.library.app.version} · ${exportedAt}`;
  elements.statPrompts.textContent = String(summary.promptCount);
  elements.statVersions.textContent = String(summary.versionCount);
  elements.statBoards.textContent = String(summary.boardCount);
  elements.statTags.textContent = String(summary.tagCount);
}

function renderBoards() {
  elements.boardList.innerHTML = "";
  if (!state.library) {
    elements.boardCount.textContent = "0";
    elements.boardList.append(buildEmptyState("Boards erscheinen nach dem ersten Import."));
    return;
  }

  const allButton = buildBoardCard({
    id: "all",
    title: "Alle Prompts",
    description: "Ohne Board-Filter",
    count: state.library.prompts.length,
    active: state.boardId === "all",
  });
  elements.boardList.append(allButton);

  for (const board of state.library.boards) {
    const count = resolveBoardEntries(state.library, board).length;
    const card = buildBoardCard({
      id: board.id,
      title: board.title,
      description: board.description || "Keine Beschreibung",
      count,
      active: state.boardId === board.id,
    });
    elements.boardList.append(card);
  }
  elements.boardCount.textContent = String(state.library.boards.length);
}

function buildBoardCard({ id, title, description, count, active }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `board-card${active ? " is-active" : ""}`;
  button.innerHTML = `
    <div class="board-card__title">
      <span>${escapeHtml(title)}</span>
      <span class="pill">${count}</span>
    </div>
    <p class="board-card__body">${escapeHtml(description)}</p>
  `;
  button.addEventListener("click", () => {
    state.boardId = id;
    ensureSelection();
    persistUiState();
    render();
  });
  return button;
}

function renderPrompts() {
  elements.promptList.innerHTML = "";
  const prompts = getVisiblePrompts();
  elements.promptCount.textContent = `${prompts.length} Treffer`;

  if (!state.library) {
    elements.promptList.append(buildEmptyState("Importiere zuerst eine Bibliothek."));
    return;
  }
  if (!prompts.length) {
    elements.promptList.append(buildEmptyState("Für diese Suche oder dieses Board gibt es keine Treffer."));
    return;
  }

  for (const prompt of prompts) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `prompt-card${state.promptId === prompt.id ? " is-active" : ""}`;
    card.innerHTML = `
      <div class="prompt-card__title">
        <span>${escapeHtml(prompt.title)}</span>
        <span class="pill">${prompt.versions.length} Versionen</span>
      </div>
      <p class="prompt-card__body">${escapeHtml(prompt.purpose || "Ohne Zweckbeschreibung")}</p>
      <div class="tag-list">
        ${prompt.tags.slice(0, 4).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
      </div>
    `;
    card.addEventListener("click", () => {
      state.promptId = prompt.id;
      state.versionId = "";
      persistUiState();
      render();
    });
    elements.promptList.append(card);
  }
}

function renderDetail() {
  const prompt = getSelectedPrompt();
  const version = resolveSelectedVersion(prompt, state.versionId);
  elements.detailMeta.innerHTML = "";
  elements.versionSelect.innerHTML = "";

  if (!prompt) {
    elements.detailTitle.textContent = "Noch nichts ausgewählt";
    elements.detailPurpose.textContent =
      state.library == null
        ? "Lade eine Bibliothek und wähle links ein Prompt oder Board."
        : "Wähle ein Prompt aus der Trefferliste.";
    elements.detailTextLabel.textContent = "Aktueller Stand";
    elements.detailText.textContent = "Noch kein Prompt gewählt.";
    elements.detailResult.textContent = "Kein Ergebnis vorhanden.";
    elements.copyButton.disabled = true;
    elements.versionSelect.disabled = true;
    return;
  }

  elements.detailTitle.textContent = prompt.title;
  elements.detailPurpose.textContent = prompt.purpose || "Ohne Zweckbeschreibung";
  elements.copyButton.disabled = false;
  elements.versionSelect.disabled = false;
  elements.detailTextLabel.textContent = version ? `Version ${version.version_number}` : "Aktueller Stand";

  const activeTags = version?.tags?.length ? version.tags : prompt.tags;
  const meta = [
    { label: "Tags", value: activeTags.length ? activeTags.join(", ") : "–" },
    { label: "Aktualisiert", value: formatDate(version?.updated_at ?? prompt.updated_at) },
    { label: "Erstellt", value: formatDate(prompt.created_at) },
  ];
  const boards = state.library.boards.filter((board) =>
    board.items.some((item) => item.prompt_id === prompt.id),
  );
  if (boards.length) {
    meta.push({ label: "Boards", value: boards.map((board) => board.title).join(", ") });
  }
  for (const entry of meta) {
    const chip = document.createElement("span");
    chip.className = "tag";
    chip.textContent = `${entry.label}: ${entry.value}`;
    elements.detailMeta.append(chip);
  }

  const currentOption = new Option("Aktueller Prompt", "", state.versionId === "", state.versionId === "");
  elements.versionSelect.append(currentOption);
  const versions = [...prompt.versions].sort((left, right) => right.version_number - left.version_number);
  for (const currentVersion of versions) {
    const option = new Option(
      `Version ${currentVersion.version_number}: ${currentVersion.title}`,
      currentVersion.id,
      state.versionId === currentVersion.id,
      state.versionId === currentVersion.id,
    );
    elements.versionSelect.append(option);
  }

  elements.detailText.textContent = version?.text ?? prompt.text ?? "";
  elements.detailResult.textContent =
    (version?.result ?? prompt.last_result ?? "").trim() || "Kein Ergebnis vorhanden.";
}

function buildEmptyState(text) {
  const node = document.createElement("div");
  node.className = "empty-state";
  node.textContent = text;
  return node;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 2800);
}

function formatDate(value) {
  if (!value) {
    return "–";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("de-DE");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      showToast("Service Worker konnte nicht registriert werden.");
    });
  });
}
