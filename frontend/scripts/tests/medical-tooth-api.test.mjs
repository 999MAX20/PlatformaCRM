import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(apiClient) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalTooth.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  });
  vm.runInNewContext(outputText, { exports, require: (name) => {
    assert.equal(name, "./client");
    return { apiClient };
  } });
  return exports.medicalToothApi;
}

test("surface choices preserve policy labels, empty configuration and either treatment basis without caching", async () => {
  const calls = [];
  const results = [
    { tooth: 11, configured: true, reference: "approved-v2", surfaces: [{ code: "a", labels: { ru: "A RU", kk: "A KK", en: "A EN" } }] },
    { tooth: 11, configured: false, reference: null, surfaces: [] },
    { tooth: 51, configured: true, reference: "legacy", surfaces: [{ code: "b", labels: {} }] },
  ];
  const api = load({ get: async (...args) => { calls.push(args); return { data: results[calls.length - 1] }; } });
  const signal = new AbortController().signal;
  const appointment = { business_id: 2, patient_id: 3, appointment_id: 4, tooth: 11 };
  const participation = { business_id: 2, patient_id: 3, participation_id: 5, tooth: 51 };
  assert.equal(await api.surfaceOptions(appointment, signal), results[0]);
  assert.equal(await api.surfaceOptions(appointment, signal), results[1]);
  assert.equal(await api.surfaceOptions(participation, signal), results[2]);
  assert.equal(calls.length, 3);
  for (const [index, [path, config]] of calls.entries()) {
    assert.equal(path, "/api/medical/tooth-observations/surface-options/");
    assert.equal(config.params, index === 2 ? participation : appointment);
    assert.equal(config.signal, signal);
  }
});

test("snapshot retains date offset, tenant, treatment basis, cursor and signal without caching", async () => {
  const calls = [];
  const api = load({ get: async (...args) => {
    calls.push(args);
    return { data: { observations: [], next_after_state_id: 8, as_of: "2026-11-22T11:00:00+05:00" } };
  } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 3, appointment_id: 4,
    as_of: "2026-11-22T11:00:00+05:00", after_state_id: 5, limit: 2 };
  const first = await api.snapshot(scope, signal);
  const second = await api.snapshot(scope, signal);
  assert.notEqual(first, second);
  assert.equal(first.next_after_state_id, 8); // Empty pages may still have a next cursor.
  assert.equal(calls.length, 2);
  for (const [path, config] of calls) {
    assert.equal(path, "/api/medical/tooth-observations/snapshot/");
    assert.equal(config.params, scope);
    assert.equal(config.signal, signal);
  }
});

test("history and exact version preserve participation basis and revision cursor", async () => {
  const calls = [];
  const result = { history_id: 7, revision: 1, current_revision: 3 };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 3, participation_id: 4 };
  const historyScope = { ...scope, tooth_state_id: 6, before_revision: 3, limit: 1 };
  assert.equal(await api.history(historyScope, signal), result);
  assert.equal(await api.version(7, scope, signal), result);
  assert.equal(calls[0][0], "/api/medical/tooth-observations/history/");
  assert.equal(calls[0][1].params, historyScope);
  assert.equal(calls[1][0], "/api/medical/tooth-observations/7/");
  assert.equal(calls[1][1].params, scope);
  assert.equal(calls[1][1].signal, signal);
});

test("save preserves clinical whitespace, revision zero, protocol and caller retry key", async () => {
  const calls = [];
  const result = { history_id: 7, tooth_state_id: 6, revision: 1, replayed: false };
  const api = load({ post: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const payload = { business_id: 2, patient_id: 3, encounter_id: 4, tooth: 51, surface: "",
    expected_patient_revision: 1, expected_encounter_revision: 2, expected_tooth_revision: 0,
    observation: "  Оқу\n", reason: "  " };
  assert.equal(await api.save(payload, "stable-key", signal), result);
  await api.save(payload, "stable-key", signal);
  for (const [path, body, config] of calls) {
    assert.equal(path, "/api/medical/tooth-observations/");
    assert.equal(body, payload);
    assert.equal(config.headers["Idempotency-Key"], "stable-key");
    assert.equal(config.signal, signal);
  }
});

test("invalid command keys do not dispatch a write", async () => {
  let calls = 0;
  const api = load({ post: async () => { calls += 1; } });
  for (const key of ["", "  ", "x".repeat(129)]) {
    await assert.rejects(api.save({}, key), /idempotency key/);
  }
  assert.equal(calls, 0);
});

test("denial, stale write, outage and abort propagate unchanged without automatic retry", async () => {
  for (const error of [{ status: 401 }, { status: 403 }, { status: 409 }, { status: 503 }, { code: "ERR_CANCELED" }]) {
    let calls = 0;
    const fail = async () => { calls += 1; throw error; };
    const api = load({ get: fail, post: fail });
    const scope = { business_id: 2, patient_id: 3, appointment_id: 4 };
    for (const request of [() => api.snapshot(scope), () => api.history({ ...scope, tooth_state_id: 6 }),
      () => api.version(7, scope), () => api.surfaceOptions({ ...scope, tooth: 11 }), () => api.save({}, "stable-key")]) {
      await assert.rejects(request(), (caught) => caught === error);
    }
    assert.equal(calls, 5);
  }
});
