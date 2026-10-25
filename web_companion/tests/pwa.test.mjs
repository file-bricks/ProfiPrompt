import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { applyLocale, getAvailableLanguages, loadLocaleCatalog, REQUIRED_UI_KEYS, translate } from "../i18n.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const manifest = JSON.parse(readFileSync(resolve(root, "manifest.webmanifest"), "utf8"));
const swSrc = readFileSync(resolve(root, "service-worker.js"), "utf8");
const indexSrc = readFileSync(resolve(root, "index.html"), "utf8");
const appSrc = readFileSync(resolve(root, "app.js"), "utf8");
const cssSrc = readFileSync(resolve(root, "app.css"), "utf8");
const localeCatalog = JSON.parse(readFileSync(resolve(root, "translations.json"), "utf8"));
const WORLDSET_LOCALES = ["en", "de", "es", "zh", "ja", "ru", "fr", "hi", "ar", "bn", "pt"];

// --- manifest tests ---

test("manifest has display:standalone", () => {
  assert.equal(manifest.display, "standalone");
});

test("manifest has start_url", () => {
  assert.ok(manifest.start_url, "start_url muss gesetzt sein");
});

test("manifest has id field (PWA-Installierbarkeit)", () => {
  assert.ok(manifest.id !== undefined, "id fehlt im manifest");
});

test("manifest has scope field", () => {
  assert.ok(manifest.scope !== undefined, "scope fehlt im manifest");
});

test("manifest has name and short_name", () => {
  assert.ok(manifest.name, "name fehlt");
  assert.ok(manifest.short_name, "short_name fehlt");
});

test("manifest declares 192x192 any-icon (PNG)", () => {
  const icon = manifest.icons.find(
    (i) => i.sizes === "192x192" && (!i.purpose || i.purpose === "any"),
  );
  assert.ok(icon, "192x192 any-icon fehlt");
  assert.match(icon.src, /\.png$/i, "192-Icon sollte PNG sein");
});

test("manifest declares 512x512 any-icon (PNG)", () => {
  const icon = manifest.icons.find(
    (i) => i.sizes === "512x512" && (!i.purpose || i.purpose === "any"),
  );
  assert.ok(icon, "512x512 any-icon fehlt");
  assert.match(icon.src, /\.png$/i, "512-Icon sollte PNG sein");
});

test("manifest has maskable icon", () => {
  const maskable = manifest.icons.find((i) => i.purpose === "maskable");
  assert.ok(maskable, "maskable icon fehlt");
});

test("all manifest icon files exist on disk", () => {
  for (const icon of manifest.icons) {
    const rel = icon.src.replace(/^\.\//, "");
    const absPath = resolve(root, rel);
    assert.ok(existsSync(absPath), `Icon-Datei fehlt: ${icon.src}`);
  }
});

// --- service-worker tests ---

test("SW CACHE_NAME enthält 'profiprompt'", () => {
  assert.match(swSrc, /profiprompt/i);
});

test("SW CACHE_NAME ist v7 und enthält die lokalisierte Offline-Laufzeit", () => {
  assert.match(swSrc, /profiprompt-companion-v7/);
  assert.doesNotMatch(swSrc, /profiprompt-companion-v2/);
});

test("SW hat skipWaiting()", () => {
  assert.match(swSrc, /skipWaiting\(\)/);
});

test("SW hat clients.claim()", () => {
  assert.match(swSrc, /clients\.claim\(\)/);
});

test("SW fetch handler prüft response.status vor Cache-Eintrag (Bug #1 Fix)", () => {
  assert.match(swSrc, /response\.status\s*!==\s*200/);
  assert.match(swSrc, /response\.type\s*===\s*["']opaque["']/);
});

test("alle manifest-PNG-Icons sind in SW ASSETS enthalten (Bug #2 Fix)", () => {
  const pngIcons = manifest.icons.filter((i) => i.src.endsWith(".png"));
  for (const icon of pngIcons) {
    assert.ok(
      swSrc.includes(icon.src),
      `Manifest-Icon fehlt in SW ASSETS: ${icon.src}`,
    );
  }
});

// --- HTML integration tests ---

test("index.html verweist auf manifest.webmanifest", () => {
  assert.match(indexSrc, /manifest\.webmanifest/);
});

test("app.js registriert service-worker.js", () => {
  assert.match(appSrc, /service-worker\.js/);
});

// --- Bug-Fix-Regressionstests ---

test("SW fetch nutzt ignoreSearch:true (Bug #1 Fix — Offline bei ?-Params)", () => {
  assert.match(swSrc, /ignoreSearch\s*:\s*true/);
});

test("index.html hat apple-touch-icon (Bug #4 Fix — iOS Homescreen)", () => {
  assert.match(indexSrc, /rel="apple-touch-icon"/);
});

test("app.js nullt deferredInstallPrompt vor prompt() (Bug #2 Fix — kein Doppel-Trigger)", () => {
  assert.match(appSrc, /deferredInstallPrompt\s*=\s*null/);
  assert.match(appSrc, /pendingPrompt\.prompt\(\)/);
});

test("app.js ensureSelection setzt stale boardId zurück (Bug #3 Fix)", () => {
  assert.match(appSrc, /state\.boardId\s*!==\s*["']all["']/);
  assert.match(appSrc, /state\.library\.boards\.some/);
});

test("app.js fallbackCopy entfernt textarea via finally (Bug #5 Fix — kein DOM-Leak)", () => {
  assert.match(appSrc, /finally\s*\{[\s\S]*?area\.remove\(\)/);
});

// --- iOS PWA-Härtung (P4b, 2026-06-16) ---

test("index.html viewport enthält viewport-fit=cover", () => {
  assert.match(indexSrc, /viewport-fit=cover/);
});

test("index.html apple-touch-icon zeigt auf apple-touch-icon-180.png (kein maskable-Icon)", () => {
  assert.match(indexSrc, /apple-touch-icon.*apple-touch-icon-180\.png/s);
  assert.doesNotMatch(indexSrc, /apple-touch-icon.*Icon-maskable/s);
});

test("index.html hat apple-mobile-web-app-title", () => {
  assert.match(indexSrc, /apple-mobile-web-app-title/);
});

test("index.html hat apple-mobile-web-app-status-bar-style", () => {
  assert.match(indexSrc, /apple-mobile-web-app-status-bar-style/);
});

test("index.html setzt KEIN apple-mobile-web-app-capable (deprecated seit iOS 11.3)", () => {
  assert.doesNotMatch(indexSrc, /apple-mobile-web-app-capable/);
});

test("apple-touch-icon-180.png existiert auf Disk", () => {
  assert.ok(existsSync(resolve(root, "icons/apple-touch-icon-180.png")));
});

test("apple-touch-icon-180.png ist in SW ASSETS enthalten", () => {
  assert.match(swSrc, /apple-touch-icon-180\.png/);
});

test("app.css enthält safe-area-inset-Werte für .shell", () => {
  assert.match(cssSrc, /safe-area-inset/);
});

test("app.css nutzt env(safe-area-inset-bottom) im toast", () => {
  assert.match(cssSrc, /safe-area-inset-bottom/);
});


async function loadBoundLocaleCatalog() {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify(localeCatalog), { status: 200 });
  try {
    return await loadLocaleCatalog();
  } finally {
    globalThis.fetch = previousFetch;
  }
}

test("PWA locale catalog is complete for all 94 keys and 11 World-Set locales", async () => {
  assert.equal(Object.keys(localeCatalog).length, 94);
  assert.equal(REQUIRED_UI_KEYS.length, 94);
  assert.equal(new Set(REQUIRED_UI_KEYS).size, 94);
  for (const key of REQUIRED_UI_KEYS) {
    assert.ok(localeCatalog[key], `PWA locale key missing: ${key}`);
    for (const locale of WORLDSET_LOCALES) {
      assert.equal(typeof localeCatalog[key][locale], "string", `${key} missing ${locale}`);
      assert.ok(localeCatalog[key][locale].trim(), `${key} empty for ${locale}`);
    }
  }
  assert.deepEqual(await loadBoundLocaleCatalog(), WORLDSET_LOCALES);
});

test("PWA applies Arabic RTL, translated labels, and localized language selection", async () => {
  await loadBoundLocaleCatalog();
  const attributes = {};
  const html = { setAttribute: (name, value) => { attributes[name] = value; } };
  const description = {};
  const heading = { dataset: { i18n: "board.heading" }, textContent: "" };
  const languageLabel = { dataset: { i18n: "language.label" }, textContent: "" };
  const placeholder = { dataset: { i18nPlaceholder: "search.placeholder" }, setAttribute(name, value) { this[name] = value; } };
  const languageSelect = {
    dataset: { i18nAriaLabel: "language.label" },
    options: WORLDSET_LOCALES.map((value) => ({ value, disabled: true })),
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    value: "",
    disabled: true,
  };
  const root = {
    documentElement: html,
    title: "",
    querySelector(selector) {
      if (selector === 'meta[name="description"]') return description;
      if (selector === "#language-select") return languageSelect;
      return null;
    },
    querySelectorAll(selector) {
      if (selector === "[data-i18n]") return [heading, languageLabel];
      if (selector === "[data-i18n-placeholder]") return [placeholder];
      if (selector === "[data-i18n-aria-label]") return [languageSelect];
      return [];
    },
  };

  applyLocale("ar", root);
  assert.equal(attributes.lang, "ar");
  assert.equal(attributes.dir, "rtl");
  assert.equal(languageSelect.value, "ar");
  assert.equal(languageSelect.disabled, false);
  assert.ok(languageSelect.options.every((option) => option.disabled === false));
  assert.equal(languageSelect.attrs["aria-label"], translate("language.label", "ar"));
  assert.equal(heading.textContent, translate("board.heading", "ar"));
  assert.equal(languageLabel.textContent, translate("language.label", "ar"));
  assert.equal(placeholder.placeholder, translate("search.placeholder", "ar"));
  assert.equal(description.content, translate("html.description", "ar"));
  assert.equal(root.title, translate("html.title", "ar"));
});

test("PWA persists locale only with UI state and leaves the library record separate", () => {
  assert.match(appSrc, /elements\.languageSelect\.addEventListener\("change"/);
  assert.match(appSrc, /applyLocale\(language\);[\s\S]{0,180}persistUiState\(\)/);
  assert.match(appSrc, /state\.language = normalizeLanguage\(typeof ui\.language === "string" \? ui\.language : "de"\)/);
  const uiState = appSrc.slice(appSrc.indexOf("function persistUiState"), appSrc.indexOf("function ensureSelection"));
  assert.match(uiState, /STORAGE_KEYS\.ui/);
  assert.match(uiState, /language:\s*state\.language/);
  assert.doesNotMatch(uiState, /STORAGE_KEYS\.library/);
  assert.match(appSrc, /error\.service_worker_registration/);
  assert.match(indexSrc, /id="language-select"[^>]*data-i18n-aria-label="language\.label"/);
  assert.match(indexSrc, /<html lang="de" dir="ltr">/);
});


test("offline navigation uses the cached localized shell without an untranslated response body", () => {
  assert.match(swSrc, /event\.request\.mode === "navigate"/);
  assert.match(swSrc, /caches\.match\("\.\/index\.html"\)/);
  assert.match(swSrc, /new Response\("", \{ status: 503/);
  assert.doesNotMatch(swSrc, /new Response\("Offline"/);
});
