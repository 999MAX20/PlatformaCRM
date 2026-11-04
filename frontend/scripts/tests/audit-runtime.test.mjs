import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import net from "node:net";
import { spawnSync } from "node:child_process";
import { requireIsolatedEnvironment, requireAvailableAuditPorts } from "../../e2e/isolated-environment.mjs";
import { interactionHasBlockingIssue, visualHasBlockingIssue } from "../audit-gates.mjs";

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "zani-quality-gate-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return { ...process.env, ZANI_QUALITY_GATE: "1", DATABASE_URL: `sqlite:///${path.join(directory, "gate.sqlite3")}`,
    E2E_DJANGO_PORT: "18741", E2E_FRONTEND_PORT: "18742", E2E_API_BASE_URL: "http://127.0.0.1:18741", E2E_BASE_URL: "http://127.0.0.1:18742" };
}

test("guard accepts disposable runtime and rejects unsafe profiles before creating files", (t) => {
  const env = fixture(t);
  requireIsolatedEnvironment(env);
  for (const patch of [{ ZANI_QUALITY_GATE: "" }, { DATABASE_URL: "sqlite:///db.sqlite3" },
    { DATABASE_URL: "postgresql://localhost/working" }, { E2E_DJANGO_PORT: "8000" },
    { E2E_BASE_URL: "https://example.invalid" }, { E2E_FRONTEND_PORT: env.E2E_DJANGO_PORT }]) {
    assert.throws(() => requireIsolatedEnvironment({ ...env, ...patch }), /No setup was performed/);
  }
  assert.deepEqual(fs.readdirSync(path.dirname(env.DATABASE_URL.slice(10))), []);
});

test("occupied port refuses setup even without an HTTP health response", async (t) => {
  const env = fixture(t);
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise((resolve) => server.close(resolve)));
  env.E2E_DJANGO_PORT = String(server.address().port);
  env.E2E_API_BASE_URL = `http://127.0.0.1:${env.E2E_DJANGO_PORT}`;
  await assert.rejects(requireAvailableAuditPorts(env), /already occupied/);
  for (const entry of ["scripts/interaction-audit.mjs", "scripts/visual-audit.mjs"]) {
    const result = spawnSync(process.execPath, [entry], { cwd: new URL("../../", import.meta.url),
      env: { ...env, E2E_PYTHON: "must-not-start" }, encoding: "utf8", timeout: 10_000 });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /already occupied/);
    assert.doesNotMatch(result.stderr, /ENOENT/);
  }
});

for (const entry of ["e2e/django-e2e.mjs", "scripts/interaction-audit.mjs", "scripts/visual-audit.mjs"]) {
  test(`${entry} refuses unsafe DB before starting Python or browser`, () => {
    const result = spawnSync(process.execPath, [entry, "prepare"], { cwd: new URL("../../", import.meta.url),
      env: { ...process.env, ZANI_QUALITY_GATE: "1", DATABASE_URL: "sqlite:///db.sqlite3", E2E_PYTHON: "must-not-start" }, encoding: "utf8" });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /No setup was performed/);
    assert.doesNotMatch(result.stderr, /ENOENT|Executable doesn't exist/);
  });
}

test("interaction gate rejects missing required actions and server failures", () => {
  const state = { authRedirected: false, unexpectedError: false, visibleDialogs: 0, activeOverlays: 0 };
  const record = { beforeActions: state, apiIssues: [], actions: [{ status: "clicked", stateAfterClick: state, stateAfterClose: state }] };
  assert.equal(interactionHasBlockingIssue(record), false);
  for (const status of ["missing", "missing-prerequisite", "disabled", "failed"]) {
    assert.equal(interactionHasBlockingIssue({ ...record, actions: [{ status }] }), true);
  }
  assert.equal(interactionHasBlockingIssue({ ...record, apiIssues: [{ status: 503 }] }), true);
  assert.equal(interactionHasBlockingIssue({ ...record, actions: [{ status: "skipped-submit" }] }), false);
});

test("visual gate rejects non-auth 5xx while retaining existing checks", () => {
  const good = { authRedirected: false, authApiIssues: 0, serverApiIssues: 0, horizontalOverflow: 0, transparentSurfaceIssues: 0 };
  assert.equal(visualHasBlockingIssue(good), false);
  for (const patch of [{ serverApiIssues: 1 }, { authApiIssues: 1 }, { horizontalOverflow: 3 }, { transparentSurfaceIssues: 1 }]) {
    assert.equal(visualHasBlockingIssue({ ...good, ...patch }), true);
  }
});
