import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(client) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalDocuments.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } });
  vm.runInNewContext(outputText, { exports, Error, require: name => {
    if (name === "./client") return { apiClient: client };
    throw new Error(`Unexpected import: ${name}`);
  } });
  return exports.medicalDocumentsApi;
}

test("review read keeps exact version, scope, history cursor and cancellation", async () => {
  const calls = [];
  const result = { document_state: "draft", state_revision: 3 };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  assert.equal(await api.review({ business_id: 1, patient_id: 2, head_branch_id: 3 }, 4, 5, signal), result);
  assert.equal(calls[0][0], "/api/medical/documents/versions/4/review/");
  assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1].params)), { business_id: 1, patient_id: 2, head_branch_id: 3, before_id: 5 });
  assert.equal(calls[0][1].signal, signal);
});

test("transition sends its state revision and idempotency key and never retries an error automatically", async () => {
  const calls = [];
  const failure = { response: { status: 409 } };
  const api = load({ post: async (...args) => { calls.push(args); throw failure; } });
  const payload = { business_id: 1, patient_id: 2, appointment_id: 3,
    target: "draft", expected_state_revision: 2, reason: "Synthetic reason" };
  await assert.rejects(api.transition(4, payload, "stable-key"), error => error === failure);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/api/medical/documents/versions/4/review-transition/");
  assert.equal(calls[0][1], payload);
  assert.equal(calls[0][2].headers["Idempotency-Key"], "stable-key");
  await assert.rejects(api.transition(4, payload, " "));
  assert.equal(calls.length, 1);
});
