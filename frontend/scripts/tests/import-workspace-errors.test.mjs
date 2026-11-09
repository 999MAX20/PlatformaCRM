import test from "node:test";
import assert from "node:assert/strict";
import { describeImportErrors } from "../../src/features/importWorkspace/importViewModel.ts";
import { importWorkspace as ru } from "../../src/lib/i18n/ru/importWorkspace.ts";
import { importWorkspace as kk } from "../../src/lib/i18n/kk/importWorkspace.ts";
import { importWorkspace as en } from "../../src/lib/i18n/en/importWorkspace.ts";

for (const [language, dictionary] of Object.entries({ ru, kk, en })) {
  test(`row errors give localized correction guidance in ${language}`, () => {
    const t = key => dictionary[key] || key;
    const result = describeImportErrors({ email: ["Enter a valid email address."], client_ref: ["Select a valid source-row reference."] }, t);
    assert.ok(result.includes(dictionary["importWorkspace.validation.email"]));
    assert.ok(result.includes(dictionary["importWorkspace.validation.reference"]));
    assert.equal(result.includes("importWorkspace."), false);
    assert.equal(result.includes("client_ref"), false);
    assert.equal(describeImportErrors({ duplicate: "A possible match requires an explicit existing-record decision." }, t), dictionary["importWorkspace.validation.duplicate"]);
    assert.equal(describeImportErrors("Unrecognized internal detail", t), dictionary["importWorkspace.validation.reviewRow"]);
  });
}
