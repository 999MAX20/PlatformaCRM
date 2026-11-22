import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(apiClient) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalClinical.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  });
  vm.runInNewContext(outputText, { exports, require: (name) => {
    assert.equal(name, "./client");
    return { apiClient };
  } });
  return exports.medicalClinicalApi;
}

test("clinical reads preserve tenant, basis, cursor and cancellation without caching", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: { sequence: calls.length } }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 7, participation_id: 9, before_id: 30, limit: 5 };
  const first = await api.workspace(scope, signal);
  const second = await api.workspace(scope, signal);
  assert.notEqual(first.sequence, second.sequence);
  assert.equal(calls[0][0], "/api/medical/encounters/workspace/");
  assert.equal(calls[0][1].params, scope);
  assert.equal(calls[0][1].signal, signal);
  const historyScope = { business_id: 2, patient_id: 7, appointment_id: 11, before_revision: 4 };
  await api.history(13, historyScope, signal);
  assert.equal(calls[2][0], "/api/medical/encounters/13/revisions/");
  assert.equal(calls[2][1].params, historyScope);
  const readScope = { business_id: 2, patient_id: 7, appointment_id: 11 };
  await api.version(19, readScope, signal);
  assert.equal(calls[3][0], "/api/medical/encounters/versions/19/");
  assert.equal(calls[3][1].params, readScope);
  assert.equal(calls[3][1].signal, signal);
});

test("clinical writes retain exact payload, key and signal for caller-controlled retry", async () => {
  const calls = [];
  const result = { id: 1, version_id: 2, revision: 3, replayed: false };
  const api = load({ post: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const payload = { business_id: 2, patient_id: 7, expected_revision: 1, content: { plan: "  Оқу\n" } };
  assert.equal(await api.saveDraft(13, payload, "stable-key", signal), result);
  await api.saveDraft(13, payload, "stable-key", signal);
  for (const [path, body, config] of calls) {
    assert.equal(path, "/api/medical/encounters/13/draft/");
    assert.equal(body, payload);
    assert.equal(config.headers["Idempotency-Key"], "stable-key");
    assert.equal(config.signal, signal);
  }
  await api.openRecord({ business_id: 2, patient_id: 7, number: "L1", appointment_id: 11, expected_patient_revision: 1 }, "record");
  await api.openEncounter({ business_id: 2, patient_id: 7, appointment_id: 11, record_id: 1,
    expected_patient_revision: 1, expected_appointment_updated_at: "2026-11-22T00:00:00Z" }, "encounter");
  assert.equal(calls[2][0], "/api/medical/records/");
  assert.equal(calls[3][0], "/api/medical/encounters/");
});

test("appointment context preserves server patient identity and action flags without caching", async () => {
  const calls = [];
  const result = { business_id: 2, patient: { id: 79, client_id: 7 }, active_record: null,
    encounter: null, actions: { create_record: false, open_encounter: false, save_draft: false } };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const scope = { business_id: 2, appointment_id: 11 };
  const signal = new AbortController().signal;
  assert.equal(await api.appointmentContext(scope, signal), result);
  assert.equal(await api.appointmentContext(scope, signal), result);
  assert.equal(calls.length, 2);
  for (const [path, config] of calls) {
    assert.equal(path, "/api/medical/encounters/appointment-context/");
    assert.equal(config.params, scope);
    assert.equal(config.signal, signal);
    assert.equal(config.params.patient_id, undefined);
  }
});

test("missing or excessive idempotency keys never dispatch a medical write", async () => {
  let calls = 0;
  const api = load({ post: async () => { calls += 1; } });
  for (const key of ["", "  ", "x".repeat(129)]) {
    await assert.rejects(api.saveDraft(1, {}, key), /idempotency key/);
  }
  assert.equal(calls, 0);
});

test("authorization, conflict, outage and cancellation errors propagate without client retries", async () => {
  for (const error of [{ status: 401 }, { status: 403 }, { status: 409 }, { status: 503 }, { code: "ERR_CANCELED" }]) {
    let calls = 0;
    const api = load({ get: async () => { calls += 1; throw error; }, post: async () => { calls += 1; throw error; } });
    await assert.rejects(api.version(1, { business_id: 2, patient_id: 7, appointment_id: 11 }), (caught) => caught === error);
    await assert.rejects(api.saveDraft(1, {}, "key"), (caught) => caught === error);
    await assert.rejects(api.appointmentContext({ business_id: 2, appointment_id: 11 }), (caught) => caught === error);
    assert.equal(calls, 3);
  }
});
