import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const htmlPath = new URL("../index.html", import.meta.url);

test("import action uses a visible button while the file input stays out of tab order", async () => {
  const html = await readFile(htmlPath, "utf8");

  assert.match(
    html,
    /<button id="import-trigger" class="button button--primary" type="button">\s*Bibliothek importieren\s*<\/button>/,
  );
  assert.match(
    html,
    /<input\s+id="import-file"[\s\S]*class="file-input-visually-hidden"[\s\S]*tabindex="-1"[\s\S]*aria-hidden="true"/,
  );
  assert.doesNotMatch(html, /<label class="button button--primary file-picker">/);
});
