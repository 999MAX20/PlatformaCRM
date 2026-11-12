import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const jwt = (user, sid) => `header.${Buffer.from(JSON.stringify({ user_id: user, sid, exp: Math.floor(Date.now() / 1000) + 600 })).toString("base64url")}.signature`;
function fixture() {
  let generation = 0, access = jwt(1, "old"), response = async () => ({ data: { ok: true, access: jwt(1, "replacement") } });
  const storage = { getGeneration: () => generation, getAccess: () => access, getUserId: () => "1", setAccess: value => { access = value; }, clear: () => { generation++; access = null; } };
  const axios = { CanceledError: class extends Error {}, isAxiosError: value => value?.isAxiosError === true,
    post: (...args) => response(...args), get: async () => ({ data: { csrf_token: "synthetic" } }) };
  const modules = { axios: { default: axios }, "../lib/storage": { tokenStorage: storage }, "./client": { apiClient: { defaults: {} }, handleSessionRecoveryError() {} } };
  function load(path, name) {
    const exports = {};
    const source = fs.readFileSync(new URL(path, import.meta.url), "utf8").replace("import.meta.env.VITE_API_URL", '""');
    vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText,
      { exports, require: name => { assert.ok(name in modules, name); return modules[name]; }, navigator: {}, atob: value => Buffer.from(value, "base64").toString(), Date });
    modules[name] = exports;
    return exports;
  }
  load("../../src/api/sessionIdentity.ts", "./sessionIdentity");
  const token = load("../../src/api/token.ts", "./token");
  const auth = load("../../src/api/auth.ts", "./auth");
  return { auth, token, storage, respond: fn => { response = fn; } };
}

test("password replacement is accepted inside the cookie lock before queued work", async () => {
  const f = fixture(); let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  f.respond(() => new Promise(resolve => { release = resolve; entered(); }));
  const change = f.auth.changePassword({}); await started;
  const next = f.token.sessionCookieRequest(0, () => f.storage.getAccess());
  const replacement = jwt(1, "replacement");
  release({ data: { ok: true, access: replacement } });
  await change;
  assert.equal(await next, replacement);
  assert.equal(f.storage.getGeneration(), 0);
});

test("replacement cannot change the account and malformed access is rejected", async () => {
  for (const replacement of [jwt(2, "foreign"), "malformed", undefined]) {
    const f = fixture(), previous = f.storage.getAccess();
    f.respond(async () => ({ data: { ok: true, access: replacement } }));
    await assert.rejects(f.auth.changePassword({}), /Invalid password-change/);
    assert.equal(f.storage.getAccess(), previous);
  }
});

test("late password response never restores a cleared or replaced browser identity", async () => {
  const f = fixture(); let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  f.respond(() => new Promise(resolve => { release = resolve; entered(); }));
  const change = f.auth.changePassword({}); await started;
  f.storage.clear(); const other = jwt(2, "other"); f.storage.setAccess(other);
  release({ data: { ok: true, access: jwt(1, "replacement") } });
  await assert.rejects(change, /Authentication session changed/);
  assert.equal(f.storage.getAccess(), other);
});
