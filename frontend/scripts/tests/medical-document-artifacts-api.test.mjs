import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(client) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalDocumentArtifacts.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } });
  vm.runInNewContext(outputText, { exports, Blob, Error, require: name => {
    if (name === "./client") return { apiClient: client };
    if (name === "axios") return { default: { isAxiosError: value => Boolean(value?.isAxiosError) } };
    throw new Error(`Unexpected import: ${name}`);
  } });
  return exports.medicalDocumentArtifactsApi;
}

test("prepare and preview preserve each access basis, saved version, locale and cancellation", async () => {
  for (const basis of ["appointment_id", "participation_id", "correction_access_id", "head_branch_id"]) {
    const calls = [];
    const file = new Blob(["%PDF-synthetic"], { type: "application/pdf" });
    const result = { artifact_id: 19, scan_status: "pending" };
    const api = load({
      post: async (...args) => { calls.push(args); return { data: result }; },
      get: async (...args) => { calls.push(args); return { data: file }; },
    });
    const signal = new AbortController().signal;
    const scope = { business_id: 1, patient_id: 2, [basis]: 3, encounter_id: 4, document_text: "must not leave workspace" };
    assert.equal(await api.prepare(scope, 17, "kk", signal), result);
    assert.equal(await api.preview(scope, 17, "kk", signal), file);
    assert.equal(calls[0][0], "/api/medical/documents/versions/17/pdf-prepare/");
    assert.equal(calls[1][0], "/api/medical/documents/versions/17/pdf/");
    for (const params of [calls[0][1], calls[1][1].params]) {
      assert.deepEqual(JSON.parse(JSON.stringify(params)), { business_id: 1, patient_id: 2, [basis]: 3, language: "kk" });
    }
    assert.equal(calls[0][2].signal, signal);
    assert.equal(calls[1][1].signal, signal);
    assert.equal(calls[1][1].responseType, "blob");
  }
});

test("quarantine and denial JSON retain their HTTP status and do not retry automatically", async () => {
  for (const status of [401, 403, 423, 503]) {
    let attempts = 0;
    const failure = { isAxiosError: true, response: { status,
      data: new Blob([JSON.stringify({ detail: "Synthetic failure" })], { type: "application/json" }) } };
    const api = load({ get: async () => { attempts++; throw failure; } });
    await assert.rejects(api.preview({ business_id: 1, patient_id: 2, appointment_id: 3 }, 17, "ru"), error => {
      assert.equal(error, failure);
      assert.equal(error.response.status, status);
      assert.equal(error.response.data.detail, "Synthetic failure");
      return true;
    });
    assert.equal(attempts, 1);
  }
});

test("malformed or oversized error bodies preserve the original failure", async () => {
  for (const content of ["not-json", "x".repeat(65537)]) {
    const blob = new Blob([content], { type: "application/json" });
    const failure = { isAxiosError: true, response: { status: 503, data: blob } };
    const api = load({ get: async () => { throw failure; } });
    await assert.rejects(api.preview({ business_id: 1, patient_id: 2, appointment_id: 3 }, 17, "ru"), error => {
      assert.equal(error, failure);
      assert.equal(error.response.data, blob);
      return true;
    });
  }
});

test("download and print post exact scope, propagate cancellation and never retry export", async () => {
  for (const purpose of ["download", "print"]) {
    const calls = [];
    const file = new Blob(["%PDF-synthetic"]);
    const api = load({ post: async (...args) => { calls.push(args); return { data: file }; } });
    const signal = new AbortController().signal;
    assert.equal(await api.export({ business_id: 1, patient_id: 2, head_branch_id: 3, document_text: "omit" }, 17, "kk", purpose, signal), file);
    assert.equal(calls[0][0], `/api/medical/documents/versions/17/pdf-${purpose}/`);
    assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1])), { business_id: 1, patient_id: 2, head_branch_id: 3, language: "kk" });
    assert.equal(calls[0][2].signal, signal);
    assert.equal(calls[0][2].responseType, "blob");
    let attempts = 0;
    const failure = { isAxiosError: true, response: { status: 403, data: new Blob(['{"detail":"Denied"}'], { type: "application/json" }) } };
    const denied = load({ post: async () => { attempts++; throw failure; } });
    await assert.rejects(denied.export({ business_id: 1, patient_id: 2, head_branch_id: 3 }, 17, "kk", purpose), error => {
      assert.equal(error.response.status, 403); assert.equal(error.response.data.detail, "Denied"); return true;
    });
    assert.equal(attempts, 1);
  }
});

test("history sends only exact version basis and cursor without document text or language", async () => {
  const calls = [];
  const result = { results: [], next_before_id: null };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  assert.equal(await api.history({ business_id: 1, patient_id: 2, correction_access_id: 3, language: "ru", document_text: "omit" }, 17, 25, signal), result);
  assert.equal(calls[0][0], "/api/medical/documents/versions/17/export-history/");
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1].params)), { business_id: 1, patient_id: 2, correction_access_id: 3, before_id: 25 });
  assert.equal(calls[0][1].signal, signal);
});
