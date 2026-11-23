import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(apiClient, common = false) {
  function evaluate(filename) {
    const exports = {};
    const source = fs.readFileSync(new URL(`../../src/api/${filename}.ts`, import.meta.url), "utf8");
    const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } });
    vm.runInNewContext(outputText, { exports, Blob, require: name => {
      if (name === "./client") return { apiClient };
      if (name === "axios") return { default: { isAxiosError: value => Boolean(value?.isAxiosError) } };
      assert.equal(name, "./medicalDocumentArtifacts");
      return evaluate("medicalDocumentArtifacts");
    } });
    return exports;
  }
  const exports = evaluate("medicalTemplates");
  return common ? exports.commonTemplatesApi : exports.medicalTemplatesApi;
}

test("template DOCX retains scope and decodes bounded JSON blob failures", async () => {
  const calls = [];
  const file = new Blob(["synthetic docx"]);
  const api = load({ get: async (...args) => { calls.push(args); return { data: { can_docx: true } }; },
    post: async (...args) => { calls.push(args); return { data: file }; } });
  const signal = new AbortController().signal;
  assert.equal((await api.docxAccess(8, 99, signal)).can_docx, true);
  assert.equal(await api.downloadDocx(8, 99, "kk", signal), file);
  assert.equal(calls[0][0], "/api/medical/document-templates/versions/99/docx-access/");
  assert.equal(calls[0][1].params.business_id, 8);
  assert.equal(calls[1][0], "/api/medical/document-templates/versions/99/docx-download/");
  assert.equal(calls[1][1].language, "kk");
  assert.equal(calls[1][1].business_id, 8);
  assert.equal(calls[1][2].signal, signal);
  assert.equal(calls[1][2].responseType, "blob");
  const failure = { isAxiosError: true, response: { status: 403,
    data: new Blob([JSON.stringify({ detail: "Access revoked" })], { type: "application/json" }) } };
  await assert.rejects(load({ post: async () => { throw failure; } }).downloadDocx(8, 99, "ru"),
    error => error === failure && error.response.data.detail === "Access revoked" && error.response.status === 403);
});

test("template reads preserve business, cursor, exact version and cancellation", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: { request: calls.length } }; } });
  const signal = new AbortController().signal;
  await api.access(8, signal);
  await api.list(8, 41, signal);
  await api.history(8, 12, 4, signal);
  await api.version(8, 99, signal);
  await api.pending(8, 21, signal);
  await api.review(8, 99, signal);
  assert.deepEqual(calls.map(call => call[0]), ["workspace-access/", "", "12/revisions/", "versions/99/", "pending-reviews/", "versions/99/review/"].map(path => "/api/medical/document-templates/" + path));
  for (const [, config] of calls) { assert.equal(config.params.business_id, 8); assert.equal(config.signal, signal); }
  assert.equal(calls[1][1].params.before_id, 41);
  assert.equal(calls[2][1].params.before_revision, 4);
  assert.equal(calls[4][1].params.before_id, 21);
  assert.notEqual((await api.version(8, 99)).request, (await api.version(8, 99)).request);
});

test("template commands preserve text, revision and caller retry key", async () => {
  const calls = [];
  const api = load({ post: async (...args) => { calls.push(args); return { data: { id: 12 } }; } });
  const payload = { business_id: 8, title: "Synthetic", text: " Literal\n{{patient}} ", reason: "Synthetic reason" };
  await api.create(payload, "same-key");
  await api.create(payload, "same-key");
  const update = { ...payload, expected_revision: 4 };
  await api.update(12, update, "update-key");
  assert.equal(calls[0][1], payload);
  assert.equal(calls[0][2].headers["Idempotency-Key"], calls[1][2].headers["Idempotency-Key"]);
  assert.equal(calls[2][0], "/api/medical/document-templates/12/draft/");
  assert.equal(calls[2][1], update);
  for (const key of ["", " ", "x".repeat(129)]) await assert.rejects(api.create(payload, key));
  assert.equal(calls.length, 3);
});

test("review commands bind exact version and preserve retry key and decision reason", async () => {
  const calls = [];
  const api = load({ post: async (...args) => { calls.push(args); return { data: {} }; } });
  await api.submit(99, { business_id: 8 }, "submit-key");
  const decision = { business_id: 8, decision: "rejected", reason: " Literal\nreason " };
  await api.decide(99, decision, "decision-key");
  await api.decide(99, decision, "decision-key");
  assert.equal(calls[0][0], "/api/medical/document-templates/versions/99/submit/");
  assert.equal(calls[1][0], "/api/medical/document-templates/versions/99/decision/");
  assert.equal(calls[1][1], decision);
  assert.equal(calls[1][2].headers["Idempotency-Key"], calls[2][2].headers["Idempotency-Key"]);
  await assert.rejects(api.submit(99, { business_id: 8 }, ""));
  await assert.rejects(api.decide(99, decision, "x".repeat(129)));
  assert.equal(calls.length, 3);
});

test("common commands and reads use common routes without changing approval route", async () => {
  const calls = [];
  const handler = async (...args) => { calls.push(args); return { data: {} }; };
  const api = load({ get: handler, post: handler }, true);
  const signal = new AbortController().signal;
  await api.access(8, signal); await api.list(8, 4, signal);
  await api.history(8, 12, 3, signal); await api.version(8, 99, signal);
  const payload = { business_id: 8, title: "Synthetic", text: "", reason: "" };
  await api.create(payload, "create"); await api.update(12, { ...payload, expected_revision: 1 }, "update");
  await api.submit(99, { business_id: 8 }, "submit");
  await api.decide(99, { business_id: 8, decision: "approved", reason: "" }, "approve");
  assert.deepEqual(calls.map(call => call[0]), ["common/workspace-access/", "common/", "common/12/revisions/", "common/versions/99/", "common/", "common/12/draft/", "common/versions/99/submit/", "versions/99/decision/"].map(path => "/api/medical/document-templates/" + path));
  assert.equal(calls[0][1].signal, signal);
  assert.equal(calls[4][1], payload);
  assert.equal(calls[6][2].headers["Idempotency-Key"], "submit");
});
