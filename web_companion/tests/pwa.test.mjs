import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const manifest = JSON.parse(readFileSync(resolve(root, "manifest.webmanifest"), "utf8"));
const swSrc = readFileSync(resolve(root, "service-worker.js"), "utf8");
const indexSrc = readFileSync(resolve(root, "index.html"), "utf8");
const appSrc = readFileSync(resolve(root, "app.js"), "utf8");
const cssSrc = readFileSync(resolve(root, "app.css"), "utf8");

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

test("SW CACHE_NAME ist v3 (nicht mehr v2)", () => {
  assert.match(swSrc, /profiprompt-companion-v3/);
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
