import test from "node:test";
import assert from "node:assert/strict";

import {
  SCHEMA_VERSION,
  buildMobileGuide,
  buildCopyText,
  detectClientPlatform,
  filterPrompts,
  normalizeLibraryPayload,
  parseStoredLibrary,
  resolveBoardEntries,
  summarizeLibrary,
} from "../library.js";

function makeLibrary() {
  return normalizeLibraryPayload({
    schema_version: SCHEMA_VERSION,
    app: {
      name: "ProfiPrompt",
      version: "1.0.1",
      exported_at: "2026-05-26T10:00:00+00:00",
    },
    stats: {
      prompt_count: 2,
      version_count: 2,
      board_count: 1,
      board_item_count: 2,
    },
    tags: ["deutsch", "review", "workflow"],
    prompts: [
      {
        id: "p1",
        title: "Code Review",
        purpose: "Patch prüfen",
        text: "Prüfe den Patch auf Regressionen.",
        tags: ["review"],
        last_result: "Gefunden: fehlender Test",
        created_at: "2026-05-26T08:00:00+00:00",
        updated_at: "2026-05-26T09:00:00+00:00",
        versions: [
          {
            id: "v1",
            prompt_id: "p1",
            version_number: 1,
            title: "Kurz",
            text: "Fasse Risiken knapp zusammen.",
            result: "",
            tags: ["workflow"],
            created_at: "2026-05-26T08:20:00+00:00",
            updated_at: "2026-05-26T08:25:00+00:00",
          },
        ],
      },
      {
        id: "p2",
        title: "Deutsch aufpolieren",
        purpose: "Umlaute prüfen",
        text: "Ersetze fehlerhafte Umschreibungen.",
        tags: ["deutsch"],
        last_result: "",
        created_at: "2026-05-26T07:00:00+00:00",
        updated_at: "2026-05-26T07:10:00+00:00",
        versions: [
          {
            id: "v2",
            prompt_id: "p2",
            version_number: 3,
            title: "Lange Version",
            text: "Achte auf ä, ö, ü und ß.",
            result: "Bereinigt",
            tags: ["deutsch"],
            created_at: "2026-05-26T07:05:00+00:00",
            updated_at: "2026-05-26T07:10:00+00:00",
          },
        ],
      },
    ],
    boards: [
      {
        id: "b1",
        title: "Lieblinge",
        description: "Schneller Zugriff",
        created_at: "2026-05-26T10:00:00+00:00",
        items: [
          {
            id: "bi1",
            board_id: "b1",
            prompt_id: "p1",
            version_id: null,
            created_at: "2026-05-26T10:01:00+00:00",
          },
          {
            id: "bi2",
            board_id: "b1",
            prompt_id: "p2",
            version_id: "v2",
            created_at: "2026-05-26T10:02:00+00:00",
          },
        ],
      },
    ],
  });
}

test("normalizeLibraryPayload keeps schema and metadata intact", () => {
  const library = makeLibrary();
  assert.equal(library.schema_version, SCHEMA_VERSION);
  assert.equal(library.prompts[0].title, "Code Review");
  assert.deepEqual(summarizeLibrary(library), {
    promptCount: 2,
    versionCount: 2,
    boardCount: 1,
    tagCount: 3,
  });
});

test("filterPrompts matches query text and board filters", () => {
  const library = makeLibrary();
  const reviewOnly = filterPrompts(library, { query: "regressionen", boardId: "all" });
  assert.deepEqual(reviewOnly.map((prompt) => prompt.id), ["p1"]);

  const boardOnly = filterPrompts(library, { query: "umlaute", boardId: "b1" });
  assert.deepEqual(boardOnly.map((prompt) => prompt.id), ["p2"]);
});

test("resolveBoardEntries links prompts and versions", () => {
  const library = makeLibrary();
  const entries = resolveBoardEntries(library, library.boards[0]);
  assert.equal(entries.length, 2);
  assert.equal(entries[1].prompt.id, "p2");
  assert.equal(entries[1].version.id, "v2");
});

test("buildCopyText mirrors the desktop copy modes", () => {
  const library = makeLibrary();
  const prompt = library.prompts[1];
  const version = prompt.versions[0];
  const text = buildCopyText(prompt, version, { mode: "all", includeMetadata: true });
  assert.match(text, /Lange Version/);
  assert.match(text, /--- Ergebnis ---/);
  assert.match(text, /\[Tags: deutsch\]/);
});

test("parseStoredLibrary restores a serialized library", () => {
  const library = makeLibrary();
  const restored = parseStoredLibrary(JSON.stringify(library));
  assert.equal(restored.prompts[0].versions[0].title, "Kurz");
});

test("detectClientPlatform differentiates Android, iOS and desktop", () => {
  assert.equal(
    detectClientPlatform("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/136.0"),
    "android",
  );
  assert.equal(
    detectClientPlatform("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"),
    "ios",
  );
  assert.equal(detectClientPlatform("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"), "desktop");
});

test("buildMobileGuide explains install and copy flows per platform", () => {
  const iosGuide = buildMobileGuide({
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15",
    hasInstallPrompt: false,
    hasLibrary: false,
  });
  assert.equal(iosGuide.platformLabel, "iPhone / iPad");
  assert.match(iosGuide.installText, /Zum Home-Bildschirm/);
  assert.match(iosGuide.copyText, /Safari/);

  const androidGuide = buildMobileGuide({
    userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/136.0",
    hasInstallPrompt: true,
    hasLibrary: true,
  });
  assert.equal(androidGuide.platformLabel, "Android");
  assert.match(androidGuide.installText, /Installieren-Schaltfläche/);
  assert.match(androidGuide.importText, /lokal gespeichert/);
});
