// Bugsweep-Regressionstests — Lauf 17, 2026-06-20
// Projekt: LLM/REL_ProfiPrompt/web_companion (~944 LOC, Vanilla JS ESM)

import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

async function src(name) {
  return readFile(resolve(root, name), "utf8");
}

// Bug #1: restoreState() — localStorage.getItem ohne äußeren try/catch
// SecurityError in Safari Private Browsing / sandboxed iframes beim Seitenstart
test("Bug #1: restoreState() hat äußeren try/catch um localStorage.getItem (SecurityError in Safari)", async () => {
  const app = await src("app.js");
  const getLibIdx = app.indexOf("localStorage.getItem(STORAGE_KEYS.library)");
  assert.ok(getLibIdx !== -1, "localStorage.getItem(STORAGE_KEYS.library) nicht gefunden");
  const before = app.slice(Math.max(0, getLibIdx - 80), getLibIdx);
  assert.ok(
    before.includes("try {"),
    "localStorage.getItem(STORAGE_KEYS.library) muss in try/catch liegen — SecurityError in Safari mit gesperrtem localStorage wirft beim Zugriff"
  );
});

// Bug #2: persistUiState() — localStorage.setItem ohne try/catch
// QuotaExceededError in Safari Private Browsing und bei vollem Speicher
test("Bug #2: persistUiState() hat try/catch um localStorage.setItem(STORAGE_KEYS.ui)", async () => {
  const app = await src("app.js");
  const setUiIdx = app.indexOf("localStorage.setItem(\n      STORAGE_KEYS.ui,");
  assert.ok(setUiIdx !== -1, "localStorage.setItem(STORAGE_KEYS.ui)-Block nicht gefunden");
  const before = app.slice(Math.max(0, setUiIdx - 20), setUiIdx);
  assert.ok(
    before.includes("try {"),
    "localStorage.setItem(STORAGE_KEYS.ui) muss in try/catch liegen — QuotaExceededError in Safari Private Browsing"
  );
});

// Bug #3+#4: onImportFileChange() + maybeLoadLibraryFromQuery() — setItem(library) ohne try/catch
test("Bug #3+#4: localStorage.setItem(STORAGE_KEYS.library) ist mindestens 2× von try/catch umgeben", async () => {
  const app = await src("app.js");
  // Zähle try { localStorage.setItem(STORAGE_KEYS.library, ...) Muster
  const regex = /try\s*\{[\s\S]{0,40}localStorage\.setItem\(STORAGE_KEYS\.library/g;
  const matches = app.match(regex) ?? [];
  assert.ok(
    matches.length >= 2,
    `localStorage.setItem(STORAGE_KEYS.library) muss mindestens 2× in try-Blöcken stehen (onImportFileChange + maybeLoadLibraryFromQuery) — gefunden: ${matches.length}`
  );
});

// Bug #5: clearLibrary() — localStorage.removeItem ohne try/catch
test("Bug #5: clearLibrary() hat try/catch um localStorage.removeItem(STORAGE_KEYS.library)", async () => {
  const app = await src("app.js");
  const removeIdx = app.indexOf("try { localStorage.removeItem(STORAGE_KEYS.library);");
  assert.ok(
    removeIdx !== -1,
    "localStorage.removeItem(STORAGE_KEYS.library) in clearLibrary() muss in try/catch liegen — SecurityError in Safari Private Browsing"
  );
});

// Bug #6: service-worker.js fetch-Handler ohne .catch()
// Unhandled Promise rejection bei Offline und nicht-gecachter Ressource
test("Bug #6: service-worker.js fetch-Handler hat .catch() als Offline-Fallback", async () => {
  const sw = await src("service-worker.js");
  assert.ok(
    sw.includes(".catch("),
    "service-worker.js fetch-Handler muss .catch() haben — unhandled rejection bei Offline + Uncached Ressource"
  );
});
