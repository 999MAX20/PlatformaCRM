import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

const names = ["Team", "Messages", "QuickReplies", "CustomFields", "Security", "Billing"];
function harness() {
  const queries = [], invalidated = [], state = [], requests = [];
  let cursor = 0;
  const api = new Proxy({}, { get: (_, method) => async (...args) => { requests.push({ method, args }); return []; } });
  const modules = {};
  const imports = {
    react: { useState: initial => { const index = cursor++; if (!(index in state)) state[index] = typeof initial === "function" ? initial() : initial; return [state[index], value => { state[index] = typeof value === "function" ? value(state[index]) : value; }]; } },
    "@tanstack/react-query": {
      useQuery: options => { queries.push(options); return { data: undefined }; },
      useMutation: options => ({ async mutateAsync(value) { const saved = await options.mutationFn(value); await options.onSuccess?.(saved, value); return saved; } }),
    },
    "../../api/team": { teamApi: api }, "../../api/appointments": { appointmentMessageSettingsApi: api },
    "../../api/quickReplies": { quickRepliesApi: api }, "../../api/customFields": { customFieldsApi: api },
    "../../api/security": { securityApi: new Proxy(api, { get: (_, key) => key === "supportGrants" ? api : api[key] }) },
    "../../api/billing": { billingApi: api },
    "../../lib/permissions": { canonicalBusinessRole: role => role || "specialist" },
    "./settingsConfig": { teamRoleOptions: [{ value: "operator" }, { value: "owner" }] },
  };
  for (const name of names) {
    const source = fs.readFileSync(new URL(`../../src/features/settings/useSettings${name}.ts`, import.meta.url), "utf8");
    const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
    const exports = {};
    vm.runInNewContext(compiled, { exports, require: name => { assert.ok(imports[name], `Unexpected import: ${name}`); return imports[name]; }, Set, window: { location: { origin: "https://example.invalid" } } });
    modules[name] = exports[`useSettings${name}`];
  }
  function render(section, permissions = true, business = { id: 7 }) {
    cursor = 0; queries.length = 0;
    const context = { business, activeSettingsSection: section, allowedSettingsSectionIds: new Set(["custom-fields"]),
      canViewTeam: permissions, canManageTeam: permissions, canManageSettings: permissions,
      canManageConversations: permissions, canViewAudit: permissions, canViewBilling: permissions,
      queryClient: { invalidateQueries: key => { invalidated.push(key); }, setQueryData() {} }, t: key => key };
    return Object.assign({}, ...names.map(name => modules[name](context)));
  }
  return { render, queries, invalidated, requests };
}

test("opening profile does not start unrelated section reads", () => {
  const h = harness(); h.render("business-profile");
  assert.equal(h.queries.filter(q => q.enabled).length, 0);
});

test("direct section entry enables only its dependencies", async () => {
  const h = harness();
  const expected = {
    "team-access": ["team-members", "team-roles", "team-invitations", "team-departments"],
    roles: ["team-members", "team-roles", "team-invitations", "team-departments"],
    "appointment-messages": ["appointment-message-settings"], "quick-replies": ["quick-replies"],
    "custom-fields": ["custom-fields"], "security-center": ["security-audit", "security-login-history", "security-support-grants"],
    usage: ["billing-entitlements"], billing: [],
  };
  for (const [section, keys] of Object.entries(expected)) {
    h.render(section);
    const enabled = h.queries.filter(q => q.enabled);
    assert.deepEqual(enabled.map(q => q.queryKey[0]).sort(), [...keys].sort(), section);
    assert.ok(enabled.every(q => q.queryKey[1] === 7));
    await Promise.all(enabled.map(q => q.queryFn()));
  }
  assert.ok(h.requests.length > 0);
});

test("denied permissions and missing Business never start domain reads", () => {
  const h = harness();
  for (const section of ["team-access", "roles", "appointment-messages", "quick-replies", "custom-fields", "security-center", "usage"]) {
    h.render(section, false); assert.equal(h.queries.filter(q => q.enabled).length, 0);
    h.render(section, true, null); assert.equal(h.queries.filter(q => q.enabled).length, 0);
  }
});

test("switching sections preserves invitation and message drafts", () => {
  const h = harness();
  let model = h.render("team-access");
  model.setInviteForm({ ...model.inviteForm, email: "draft@example.invalid" });
  model.setAppointmentMessageDrafts({ 2: { text: "unsaved" } });
  h.render("security-center"); model = h.render("team-access");
  assert.equal(model.inviteForm.email, "draft@example.invalid");
  assert.equal(model.appointmentMessageDrafts[2].text, "unsaved");
  assert.equal(harness().render("team-access").inviteForm.email, "");
});

test("custom field save still invalidates the shared field query", async () => {
  const h = harness(), model = h.render("custom-fields");
  await model.updateCustomFieldMutation.mutateAsync({ id: 3, payload: { label: "Edited" } });
  assert.equal(h.requests[0].method, "update");
  assert.equal(h.invalidated[0].queryKey[0], "custom-fields");
});
