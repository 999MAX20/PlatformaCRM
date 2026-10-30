import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const exports = {};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(new URL("../../e2e/support/auth-request.ts", import.meta.url), "utf8"),
  { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText, { exports, URL });

test("direct auth consumers reuse their cookie context and send correct origin/token", async () => {
  const calls = [], result = {};
  const request = {
    get: async url => { calls.push(url); return { ok: () => true, url: () => "https://crm.example.invalid/api/auth/csrf/", json: async () => ({ csrf_token: "masked" }) }; },
    post: async (...args) => { calls.push(args); return result; },
  };
  assert.equal(await exports.authPost(request, "/api/auth/mfa/verify/", { data: { challenge_token: "synthetic" }, headers: { "X-Test": "kept" } }), result);
  assert.equal(calls[0], "/api/auth/csrf/");
  assert.equal(calls[1][1].headers.Origin, "https://crm.example.invalid");
  assert.equal(calls[1][1].headers["X-CSRFToken"], "masked");
  assert.equal(calls[1][1].headers["X-Test"], "kept");
});

test("unavailable bootstrap does not post login or MFA credentials", async () => {
  let posted = false;
  await assert.rejects(exports.authPost({ get: async () => ({ ok: () => false, status: () => 503 }), post: async () => { posted = true; } }, "/api/auth/token/"), /503/);
  assert.equal(posted, false);
});
