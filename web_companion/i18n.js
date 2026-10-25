export const UI_LANGUAGES = [
  ["en", "English"],
  ["de", "Deutsch"],
  ["es", "Español"],
  ["zh", "简体中文"],
  ["ja", "日本語"],
  ["ru", "Русский"],
  ["fr", "Français"],
  ["hi", "हिन्दी"],
  ["ar", "العربية"],
  ["bn", "বাংলা"],
  ["pt", "Português"],
];

export const REQUIRED_UI_KEYS = [
  "html.title", "html.description", "hero.title", "hero.lead.prefix", "hero.lead.suffix",
  "language.label", "panel.status", "status.no_library", "panel.storage", "storage.local",
  "button.import", "button.clear", "stats.label", "stats.prompts", "stats.versions",
  "stats.boards", "stats.tags", "toolbar.label", "toolbar.search", "search.placeholder",
  "toolbar.copy_mode", "copy.all", "copy.title", "copy.text", "copy.result", "copy.include_tags",
  "button.install", "mobile.guide.label", "mobile.guide.eyeline", "mobile.guide.title",
  "platform.desktop", "platform.android", "platform.ios", "guide.install.label", "guide.import.label",
  "guide.offline.label", "guide.copy.label", "guide.install.ios", "guide.install.prompt",
  "guide.install.chrome", "guide.import.saved", "guide.import.empty", "guide.offline.saved",
  "guide.offline.empty", "guide.copy.ios", "guide.copy.other", "workspace.label", "board.heading",
  "board.all", "board.no_filter", "board.no_description", "board.empty", "prompt.heading",
  "prompt.count", "prompt.import_first", "prompt.no_results", "detail.empty_title", "detail.empty_purpose",
  "detail.choose_prompt", "button.copy_selection", "detail.version", "detail.prompt",
  "detail.current_version", "detail.current_prompt", "detail.current_state", "detail.empty_text",
  "detail.result", "detail.optional", "detail.empty_result", "detail.no_purpose", "meta.tags",
  "meta.updated", "meta.created", "meta.boards", "version.option", "copy_fallback.title",
  "copy_fallback.help", "copy_fallback.close", "copy_fallback.text_label", "copy_fallback.select",
  "toast.imported", "error.import_failed", "error.demo_load", "toast.demo_loaded", "error.demo_failed",
  "error.service_worker_registration", "toast.library_cleared", "toast.copy_success", "toast.clipboard_blocked", "copy.result_heading",
  "copy.tags_heading", "date.unknown", "error.invalid_json_object", "error.schema_mismatch",
];

let catalog = {};

export async function loadLocaleCatalog() {
  try {
    const response = await fetch(new URL("./translations.json", import.meta.url), { cache: "no-cache" });
    if (!response.ok) throw new Error(`locale catalog HTTP ${response.status}`);
    const payload = await response.json();
    catalog = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  } catch {
    catalog = {};
  }
  return getAvailableLanguages();
}

export function getAvailableLanguages() {
  return UI_LANGUAGES.filter(([code]) =>
    code === "de" || REQUIRED_UI_KEYS.every((key) => {
      const value = catalog[key]?.[code];
      return typeof value === "string" && value.trim().length > 0;
    }),
  ).map(([code]) => code);
}

export function normalizeLanguage(code) {
  return getAvailableLanguages().includes(code) ? code : "de";
}

export function translate(key, language = "de", values = {}) {
  const entry = catalog[key];
  let text = "";
  for (const code of [language, "en", "de"]) {
    const value = entry?.[code];
    if (typeof value === "string" && value.trim()) {
      text = value;
      break;
    }
  }
  if (!text) text = key;
  return text.replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (match, name) =>
    Object.hasOwn(values, name) ? String(values[name]) : match,
  );
}

export function applyLocale(language, root = document) {
  const code = normalizeLanguage(language);
  const html = root.documentElement ?? root;
  html.setAttribute("lang", code);
  html.setAttribute("dir", code === "ar" ? "rtl" : "ltr");
  root.title = translate("html.title", code);

  const description = root.querySelector('meta[name="description"]');
  if (description) description.content = translate("html.description", code);
  for (const node of root.querySelectorAll("[data-i18n]")) {
    node.textContent = translate(node.dataset.i18n, code);
  }
  for (const node of root.querySelectorAll("[data-i18n-placeholder]")) {
    node.setAttribute("placeholder", translate(node.dataset.i18nPlaceholder, code));
  }
  for (const node of root.querySelectorAll("[data-i18n-aria-label]")) {
    node.setAttribute("aria-label", translate(node.dataset.i18nAriaLabel, code));
  }

  const available = new Set(getAvailableLanguages());
  const selector = root.querySelector("#language-select");
  if (selector) {
    for (const option of selector.options) {
      option.disabled = !available.has(option.value);
    }
    selector.value = code;
    selector.disabled = available.size < 2;
  }
  return code;
}

export function getLocaleCatalog() {
  return catalog;
}
