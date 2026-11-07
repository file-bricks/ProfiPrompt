import test from "node:test";
import assert from "node:assert/strict";
import {
  SUPPORTED_LANGUAGES,
  LANGUAGE_NAMES,
  TRANSLATIONS,
  getTranslation,
  t,
} from "../i18n.js";

const REQUIRED_LANGUAGES = ["de", "en", "es", "zh", "ja", "ru"];

test("SUPPORTED_LANGUAGES contains all 6 Tier-2 languages", () => {
  assert.deepEqual(SUPPORTED_LANGUAGES, REQUIRED_LANGUAGES);
});

test("LANGUAGE_NAMES has entries for all 6 languages", () => {
  for (const lang of REQUIRED_LANGUAGES) {
    assert.ok(LANGUAGE_NAMES[lang], `Missing name for ${lang}`);
    assert.equal(typeof LANGUAGE_NAMES[lang], "string");
  }
});

test("TRANSLATIONS contains all 6 Tier-2 languages", () => {
  for (const lang of REQUIRED_LANGUAGES) {
    assert.ok(TRANSLATIONS[lang], `Language ${lang} missing in TRANSLATIONS`);
  }
});

test("100% key parity across all 6 languages without empty values", () => {
  const deKeys = Object.keys(TRANSLATIONS.de);
  assert.ok(deKeys.length >= 40, `Expected at least 40 keys, found ${deKeys.length}`);

  for (const lang of REQUIRED_LANGUAGES) {
    const keys = Object.keys(TRANSLATIONS[lang]);
    assert.deepEqual(
      keys.sort(),
      deKeys.sort(),
      `Keys in ${lang} do not match de keys exactly`
    );

    for (const key of deKeys) {
      const val = TRANSLATIONS[lang][key];
      assert.equal(typeof val, "string", `${lang}.${key} must be a string`);
      assert.ok(val.trim().length > 0, `${lang}.${key} must not be empty`);
    }
  }
});

test("t() interpolates parameters correctly across languages", () => {
  assert.equal(t("prompts_count_matches", { count: 5 }, "de"), "5 Treffer");
  assert.equal(t("prompts_count_matches", { count: 5 }, "en"), "5 results");
  assert.equal(t("prompts_count_matches", { count: 5 }, "es"), "5 resultados");
  assert.equal(t("prompts_count_matches", { count: 5 }, "zh"), "5 条结果");
  assert.equal(t("prompts_count_matches", { count: 5 }, "ja"), "5 件の一致");
  assert.equal(t("prompts_count_matches", { count: 5 }, "ru"), "5 рез.");

  assert.equal(t("prompt_versions_pill", { count: 3 }, "de"), "3 Versionen");
  assert.equal(t("prompt_versions_pill", { count: 3 }, "en"), "3 versions");
  assert.equal(t("prompt_versions_pill", { count: 3 }, "es"), "3 versiones");
  assert.equal(t("prompt_versions_pill", { count: 3 }, "zh"), "3 个版本");
  assert.equal(t("prompt_versions_pill", { count: 3 }, "ja"), "3 バージョン");
  assert.equal(t("prompt_versions_pill", { count: 3 }, "ru"), "3 версий");
});

test("t() falls back gracefully for unknown keys or languages", () => {
  assert.equal(t("non_existent_key_xyz", {}, "de"), "non_existent_key_xyz");
  assert.equal(t("non_existent_key_xyz", {}, "unknown_lang"), "non_existent_key_xyz");
  assert.equal(t("stat_prompts", {}, "unknown_lang"), "Prompts");
});
