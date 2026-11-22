import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(apiClient) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalParticipation.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  });
  vm.runInNewContext(outputText, { exports, require: (name) => {
    assert.equal(name, "./client");
    return { apiClient };
  } });
  return exports.medicalParticipationApi;
}

test("participation lists preserve tenant/filter/cursor and re-fetch instead of caching", async () => {
  const calls = [];
  const result = { results: [], next_before_id: 8 };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const incoming = { business_id: 2, before_id: 17, limit: 5 };
  assert.equal(await api.invitations(incoming, signal), result);
  await api.invitations(incoming, signal);
  const managed = { ...incoming, branch_id: 4, patient_id: 7, state: "active" };
  await api.managed(managed, signal);
  assert.equal(calls.length, 3);
  assert.equal(calls[0][0], "/api/medical/participations/invitations/");
  assert.equal(calls[0][1].params, incoming);
  assert.equal(calls[2][0], "/api/medical/participations/managed/");
  assert.equal(calls[2][1].params, managed);
  for (const [, config] of calls) assert.equal(config.signal, signal);
});

test("proposal destinations and outgoing preserve current source, pagination and cancellation", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: { results: [], next_after_branch_id: 8 } }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 7, source_appointment_id: 9, after_branch_id: 3, limit: 1 };
  const result = await api.proposalBranches(scope, signal);
  assert.equal(result.next_after_branch_id, 8);
  assert.equal(calls[0][0], "/api/medical/participations/proposal-branches/");
  assert.equal(calls[0][1].params, scope);
  assert.equal(calls[0][1].signal, signal);
  const outgoing = { business_id: 2, patient_id: 7, source_participation_id: 11, before_id: 5 };
  await api.outgoing(outgoing, signal);
  assert.equal(calls[1][0], "/api/medical/participations/outgoing/");
  assert.equal(calls[1][1].params, outgoing);
  assert.equal(calls[1][1].signal, signal);
});

test("workspace authorization and own participation are fetched for the current business", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: { revision: calls.length } }; } });
  const signal = new AbortController().signal;
  const first = await api.access(2, signal);
  const second = await api.access(2, signal);
  assert.notEqual(first.revision, second.revision);
  assert.equal(calls[0][0], "/api/medical/participations/workspace-access/");
  assert.equal(calls[0][1].params.business_id, 2);
  assert.equal(calls[0][1].signal, signal);
  const scope = { business_id: 3, before_id: 7, limit: 5 };
  await api.mine(scope, signal);
  assert.equal(calls[2][0], "/api/medical/participations/mine/");
  assert.equal(calls[2][1].params, scope);
  assert.equal(calls[2][1].signal, signal);
});

test("patient lookup uses client identity only to resolve a server-authorized patient", async () => {
  const scope = { business_id: 2, client_id: 77, branch_id: 3 };
  const result = { business_id: 2, patient_id: 91, branch_id: 3 };
  const signal = new AbortController().signal;
  const api = load({ get: async (path, config) => {
    assert.equal(path, "/api/medical/participations/patient-context/");
    assert.equal(config.params, scope);
    assert.equal(config.signal, signal);
    return { data: result };
  } });
  assert.equal(await api.patientContext(scope, signal), result);
});

test("candidate reads preserve an empty page continuation, revision and clinical source", async () => {
  const calls = [];
  const result = { results: [], patient_revision: 3, next_after_member_id: 14 };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 7, branch_id: 4, source_appointment_id: 9,
    query: "Ә", after_member_id: 11, limit: 2 };
  assert.equal(await api.candidates(scope, signal), result);
  assert.equal(calls[0][0], "/api/medical/participations/candidates/");
  assert.equal(calls[0][1].params, scope);
  assert.equal(calls[0][1].signal, signal);
});

test("closure candidate lookup is scoped to one participation and preserves its current revision", async () => {
  const calls = [];
  const result = { results: [], participation_revision: 4, next_after_member_id: 9 };
  const api = load({ get: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 7, after_member_id: 8, query: "Ә", limit: 1 };
  assert.equal(await api.responsibleCandidates(11, scope, signal), result);
  assert.equal(calls[0][0], "/api/medical/participations/11/responsible-candidates/");
  assert.equal(calls[0][1].params, scope);
  assert.equal(calls[0][1].signal, signal);
});

test("commands preserve exact reason, scope, revisions and caller retry key", async () => {
  const calls = [];
  const result = { id: 11, state: "ended", revision: 4, replayed: false };
  const api = load({ post: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 2, patient_id: 7, expected_revision: 3 };
  const proposal = { business_id: 2, patient_id: 7, branch_id: 4, target_member_id: 5,
    expected_patient_revision: 8, reason: "  Себеп\n", source_participation_id: 10 };
  const response = { ...scope, decision: "accept" };
  const closure = { ...scope, responsible_member_id: 19, reason: "  Причина\n" };
  await api.propose(proposal, "proposal", signal);
  await api.respond(11, response, "respond", signal);
  await api.withdraw(11, scope, "withdraw", signal);
  assert.equal(await api.endByHead(11, closure, "stable-end", signal), result);
  await api.endByHead(11, closure, "stable-end", signal);
  const paths = ["", "11/respond/", "11/withdraw/", "11/end-by-head/", "11/end-by-head/"];
  const payloads = [proposal, response, scope, closure, closure];
  const keys = ["proposal", "respond", "withdraw", "stable-end", "stable-end"];
  calls.forEach(([path, payload, config], index) => {
    assert.equal(path, `/api/medical/participations/${paths[index]}`);
    assert.equal(payload, payloads[index]);
    assert.equal(config.headers["Idempotency-Key"], keys[index]);
    assert.equal(config.signal, signal);
  });
});

test("invalid keys never dispatch any participation command", async () => {
  let calls = 0;
  const api = load({ post: async () => { calls += 1; } });
  for (const key of ["", "  ", "x".repeat(129)]) {
    await assert.rejects(api.propose({}, key), /idempotency key/);
    for (const method of ["respond", "withdraw", "endByHead"]) {
      await assert.rejects(api[method](11, {}, key), /idempotency key/);
    }
  }
  assert.equal(calls, 0);
});

test("denial, stale state, outage and cancellation propagate without automatic retry", async () => {
  for (const error of [{ status: 401 }, { status: 403 }, { status: 409 }, { status: 503 }, { code: "ERR_CANCELED" }]) {
    let calls = 0;
    const fail = async () => { calls += 1; throw error; };
    const api = load({ get: fail, post: fail });
    await assert.rejects(api.invitations({ business_id: 2 }), caught => caught === error);
    await assert.rejects(api.respond(11, {}, "retry"), caught => caught === error);
    assert.equal(calls, 2);
  }
});
