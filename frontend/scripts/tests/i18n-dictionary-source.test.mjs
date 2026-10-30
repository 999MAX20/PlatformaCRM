import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { dictionaryBlock } from "../i18n-dictionary-source.mjs";

function fixture(t, files) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "crm-dictionary-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  for (const [file, source] of Object.entries(files)) {
    const target = path.join(directory, file);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, source);
  }
  return directory;
}

test("domain imports preserve explicit keys, escaped values and override order", (t) => {
  const directory = fixture(t, {
    "ru.ts": 'import { domain as labels } from "./ru/domain"; export const ru = { ...labels, "shared": "override" };',
    "ru/domain.ts": 'export const domain = { "nested.key": "line\\nquoted \\"value\\"", "shared": "original" };',
  });
  const block = dictionaryBlock("ru", directory);
  assert.match(block, /"nested.key":/);
  assert.ok(block.indexOf('"original"') < block.indexOf('"override"'));
  assert.match(block, /line\\nquoted/);
});

test("Russian fallback never supplies missing explicit translated keys", (t) => {
  const directory = fixture(t, {
    "ru.ts": 'export const ru = { "missing": "Russian" };',
    "en.ts": 'import { ru } from "./ru"; export const en = { ...ru, "present": "English" };',
  });
  const block = dictionaryBlock("en", directory);
  assert.match(block, /^\.\.\.ru,/);
  assert.doesNotMatch(block, /"missing"/);
  assert.match(block, /"present"/);
});

test("fallback after domain translations stays detectable by the parity gate", (t) => {
  const directory = fixture(t, {
    "ru.ts": 'export const ru = { "key": "Russian" };',
    "en.ts": 'import { ru } from "./ru"; import { domain } from "./en/domain"; export const en = { ...domain, ...ru };',
    "en/domain.ts": 'export const domain = { "key": "English" };',
  });
  const block = dictionaryBlock("en", directory);
  assert.ok(block.indexOf("...ru") > block.indexOf('"key"'));
});

test("cycles and executable entries fail closed", (t) => {
  const directory = fixture(t, {
    "ru.ts": 'import { domain } from "./ru/domain"; export const ru = { ...domain };',
    "ru/domain.ts": 'import { domain } from "./domain"; export const domain = { ...domain };',
    "en.ts": 'export const en = { "key": compute() };',
  });
  assert.throws(() => dictionaryBlock("ru", directory), /Circular dictionary/);
  assert.throws(() => dictionaryBlock("en", directory), /Nonliteral dictionary/);
});
