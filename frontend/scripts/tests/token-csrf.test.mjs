import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

function fixture() {
  let generation = 0, access = null, get = async () => ({ data: { csrf_token: "masked-token" } });
  const calls = [], exports = {};
  const axios = {
    CanceledError: class extends Error {},
    get: async (...args) => { calls.push(["GET", ...args]); return get(); },
    post: async (...args) => { calls.push(["POST", ...args]); return { data: { access: "new-access" } }; },
  };
  const tokenStorage = { getGeneration: () => generation, getAccess: () => access, getUserId: () => null,
    clear() { generation++; access = null; }, setAccess(value) { access = value; }, setEmail() {} };
  const imports = { axios: { default: axios }, "../lib/storage": { tokenStorage },
    "./sessionIdentity": { readSessionIdentity: () => null, SessionIdentityChangedError: class extends Error {} } };
  const source = fs.readFileSync(new URL("../../src/api/token.ts", import.meta.url), "utf8").replace("import.meta.env.VITE_API_URL", '""');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText,
    { exports, navigator: {}, require: name => { assert.ok(name in imports, name); return imports[name]; } });
  return { api: exports, calls, tokenStorage, get: fn => { get = fn; } };
}

test("each public cookie operation obtains a token and sends it with credentials", async () => {
  for (const [method, args, endpoint] of [
    ["loginWithCredentials", [{ email: "test@example.invalid", password: "synthetic" }], "token/"],
    ["loginWithSocial", [{ provider: "google", idToken: "synthetic" }], "social/"],
    ["signupOwner", [{}], "signup/owner/"],
    ["confirmMfaEnrollment", ["challenge", "123456"], "mfa/enrollment/confirm/"],
    ["verifyMfaLogin", ["challenge", "123456"], "mfa/verify/"],
    ["refreshToken", [], "token/refresh/"],
    ["clearRefreshCookie", [], "logout/"],
    ["confirmPasswordReset", [{}], "password-reset/confirm/"],
  ]) {
    const f = fixture(); await f.api[method](...args);
    assert.equal(f.calls[0][0], "GET"); assert.equal(f.calls[0][1], "/api/auth/csrf/");
    assert.equal(f.calls[0][2].withCredentials, true);
    assert.equal(f.calls[1][1], `/api/auth/${endpoint}`);
    assert.equal(f.calls[1][3].headers["X-CSRFToken"], "masked-token");
    assert.equal(f.calls[1][3].withCredentials, true);
  }
});

test("failed bootstrap sends no credentials; a later explicit retry recovers", async () => {
  const f = fixture(); f.get(async () => { throw new Error("503"); });
  await assert.rejects(f.api.loginWithCredentials({}), /503/);
  assert.equal(f.calls.filter(call => call[0] === "POST").length, 0);
  f.get(async () => ({ data: { csrf_token: "recovered" } }));
  await f.api.loginWithCredentials({});
  assert.equal(f.calls.at(-1)[3].headers["X-CSRFToken"], "recovered");
});

test("session changes during bootstrap cancel the cookie mutation before POST", async () => {
  const f = fixture(); let release, started;
  const ready = new Promise(resolve => { started = resolve; });
  f.get(() => new Promise(resolve => { release = resolve; started(); }));
  const request = f.api.loginWithCredentials({}); await ready;
  f.tokenStorage.clear(); release({ data: { csrf_token: "old-session-token" } });
  await assert.rejects(request, /Authentication session changed/);
  assert.equal(f.calls.filter(call => call[0] === "POST").length, 0);
});

test("cookie operations refresh the CSRF token instead of reusing a deleted cookie", async () => {
  const f = fixture(); await f.api.loginWithCredentials({});
  f.get(async () => ({ data: { csrf_token: "replacement-token" } }));
  await f.api.clearRefreshCookie();
  assert.equal(f.calls.at(-1)[3].headers["X-CSRFToken"], "replacement-token");
  assert.equal(f.calls.filter(call => call[0] === "GET").length, 2);
});
