import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";
import axios from "axios";

function load(client) {
  const exports = {};
  const source = fs.readFileSync(new URL("../../src/api/medicalFiles.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } });
  vm.runInNewContext(outputText, { exports, FormData, Blob, Error, require: name => {
    if (name === "./client") return { apiClient: client };
    if (name === "axios") return { default: { isAxiosError: value => Boolean(value?.isAxiosError) } };
    throw new Error(`Unexpected import: ${name}`);
  } });
  return exports.medicalFilesApi;
}

const scope = { business_id: 1, patient_id: 2, participation_id: 3 };

test("correction upload retains its reason and exact encounter on retry", async () => {
  const calls = [];
  const api = load({ post: async (...args) => { calls.push(args); return { data: { id: 7 } }; } });
  const payload = { business_id: 1, patient_id: 2, correction_access_id: 8, record_id: 4,
    encounter_id: 9, expected_patient_revision: 5, description: "Synthetic", teeth: [21],
    reason: "Добавлен пропущенный снимок", file: new File(["%PDF-synthetic"], "test.pdf") };
  await api.upload(payload, "correction-command");
  await api.upload(payload, "correction-command");
  for (const [, form, config] of calls) {
    assert.equal(form.get("reason"), payload.reason);
    assert.equal(form.get("correction_access_id"), "8");
    assert.equal(form.get("encounter_id"), "9");
    assert.equal(form.has("appointment_id"), false);
    assert.equal(form.has("participation_id"), false);
    assert.equal(config.headers["Idempotency-Key"], "correction-command");
  }
});

test("upload preserves bytes, repeated tooth fields, retry key and cancellation signal", async () => {
  const calls = [];
  const api = load({ post: async (...args) => { calls.push(args); return { data: { id: 7 } }; } });
  const controller = new AbortController();
  const file = new File(["%PDF-synthetic"], "Учебный.pdf", { type: "application/pdf" });
  const payload = { ...scope, record_id: 4, expected_patient_revision: 5, file, teeth: [11, 21], description: "Synthetic" };
  await api.upload(payload, "same-command", controller.signal);
  await api.upload(payload, "same-command", controller.signal);
  for (const [url, form, options] of calls) {
    assert.equal(url, "/api/medical/files/");
    assert.equal(await form.get("file").text(), "%PDF-synthetic");
    assert.equal(form.get("file").name, "Учебный.pdf");
    assert.deepEqual(form.getAll("teeth"), ["11", "21"]);
    assert.equal(form.get("participation_id"), "3");
    assert.equal(form.has("appointment_id"), false);
    assert.equal(options.headers["Idempotency-Key"], "same-command");
    assert.equal(options.signal, controller.signal);
    assert.equal(options.headers["Content-Type"], "multipart/form-data");
  }
});

test("the CRM JSON default cannot serialize medical multipart data as JSON", async () => {
  let body;
  const client = axios.create({ headers: { "Content-Type": "application/json" }, adapter: async config => {
    body = config.data;
    return { data: { id: 7 }, status: 201, statusText: "Created", headers: {}, config };
  } });
  await load(client).upload({ ...scope, record_id: 4, expected_patient_revision: 5,
    file: new File(["%PDF-synthetic"], "test.pdf", { type: "application/pdf" }), teeth: [], description: "" }, "upload");
  assert.ok(body instanceof FormData);
  assert.equal(await body.get("file").text(), "%PDF-synthetic");
});

test("preview and export request the exact version with the current access basis", async () => {
  const calls = [];
  const file = new Blob(["synthetic"]);
  const api = load({ get: async (...args) => { calls.push(args); return { data: file }; } });
  assert.equal(await api.preview(scope, 8, 9), file);
  assert.equal(await api.download(scope, 8, 9), file);
  assert.deepEqual(calls.map(item => item[0]), ["/api/medical/files/8/preview/", "/api/medical/files/8/download/"]);
  for (const [, options] of calls) {
    assert.equal(options.params.version_id, 9);
    assert.equal(options.params.participation_id, 3);
    assert.equal(options.responseType, "blob");
  }
});

test("workspace fields do not leak into strict read requests or force an encounter filter", async () => {
  const calls = [];
  const api = load({ get: async (...args) => { calls.push(args); return { data: {} }; } });
  const workspace = { ...scope, record_id: 4, encounter_id: 5 };
  await api.list(workspace);
  await api.version(workspace, 7);
  await api.history(workspace, 7);
  await api.preview(workspace, 7);
  for (const [, config] of calls) {
    assert.equal(config.params.record_id, undefined);
    assert.equal(config.params.encounter_id, undefined);
    assert.equal(config.params.participation_id, 3);
  }
});

test("blob error keeps the HTTP denial and exposes the structured quarantine reason without retry", async () => {
  let calls = 0;
  const failure = { isAxiosError: true, response: { status: 423,
    data: new Blob([JSON.stringify({ code: "file_quarantined", detail: "Security check pending" })], { type: "application/json" }) } };
  const api = load({ get: async () => { calls += 1; throw failure; } });
  await assert.rejects(api.preview(scope, 8), error => {
    assert.equal(error, failure);
    assert.equal(error.response.status, 423);
    assert.equal(error.response.data.code, "file_quarantined");
    return true;
  });
  assert.equal(calls, 1);
});

test("metadata correction sends only its version, content and clinical basis", async () => {
  let sent;
  const api = load({ post: async (...args) => { sent = args; return { data: { revision: 2 } }; } });
  await api.updateMetadata(7, { ...scope, record_id: 4, encounter_id: 5, expected_revision: 1,
    description: "Updated", teeth: [21], reason: "Correction" }, "metadata-command");
  assert.equal(sent[0], "/api/medical/files/7/metadata/");
  assert.equal(sent[1].record_id, undefined);
  assert.equal(sent[1].encounter_id, undefined);
  assert.equal(sent[1].participation_id, 3);
  assert.equal(sent[1].expected_revision, 1);
  assert.equal(sent[2].headers["Idempotency-Key"], "metadata-command");
});
