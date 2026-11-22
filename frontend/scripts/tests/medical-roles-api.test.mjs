import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function load(apiClient) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalRoles.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  });
  vm.runInNewContext(outputText, { exports, require: name => {
    assert.equal(name, "./client"); return { apiClient };
  } });
  return exports.medicalRolesApi;
}

test("owner reads preserve tenant, member, cursor and cancellation without caching", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: { version: calls.length } }; } });
  const signal = new AbortController().signal;
  const scope = { business_id: 8, member_id: 12, after_id: 3, limit: 2, query: "Synthetic" };
  for (const [method, path] of [["roles", "roles"], ["members", "members"], ["context", "member-context"], ["branches", "branches"], ["history", "history"]]) {
    await api[method](scope, signal);
    const [url, config] = calls.at(-1);
    assert.equal(url, `/api/medical/role-management/${path}/`);
    assert.equal(config.params, scope); assert.equal(config.signal, signal);
  }
  assert.notEqual((await api.access(8, signal)).version, (await api.access(8, signal)).version);
  assert.equal(calls.at(-1)[0], "/api/medical/role-management/workspace/");
  assert.equal(calls.at(-1)[1].params.business_id, 8);
});

test("commands preserve revision, explicit permission scope, basis and caller retry key", async () => {
  const calls = [];
  const result = { id: 17, revision: 4, replayed: false };
  const api = load({ post: async (...args) => { calls.push(args); return { data: result }; } });
  const signal = new AbortController().signal;
  for (const [method, path, payload] of [
    ["create", "roles", { business_id: 8, name: "Deputy", kind: "head", permissions: [{ resource: "medical_records", action: "view", scope: "own" }] }],
    ["assign", "assign", { business_id: 8, member_id: 12, expected_revision: 3, role_id: 9, branch_ids: [2], all_branches: false, reason: "Synthetic basis\nSecond line" }],
    ["revoke", "revoke", { business_id: 8, member_id: 12, expected_revision: 4, reason: "Synthetic revocation" }],
  ]) {
    assert.equal(await api[method](payload, "caller-key", signal), result);
    const [url, body, config] = calls.at(-1);
    assert.equal(url, `/api/medical/role-management/${path}/`);
    assert.equal(body, payload); assert.equal(config.headers["Idempotency-Key"], "caller-key");
    assert.equal(config.signal, signal);
  }
});

test("invalid keys never send; denial, stale state and outages propagate without automatic retry", async () => {
  let calls = 0;
  let failure;
  const api = load({ post: async () => { calls++; throw failure; } });
  for (const method of ["create", "assign", "revoke"]) {
    for (const key of ["", "  ", "x".repeat(129)]) await assert.rejects(api[method]({}, key));
  }
  assert.equal(calls, 0);
  for (const status of [403, 409, 503]) {
    failure = { response: { status } };
    await assert.rejects(api.assign({}, "stable-key"), cause => cause === failure);
  }
  assert.equal(calls, 3);
});
