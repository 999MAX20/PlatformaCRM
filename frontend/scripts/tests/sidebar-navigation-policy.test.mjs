import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const root = new URL("../../src/", import.meta.url);
const read = (path) => readFile(new URL(path, root), "utf8");

function evaluate(source, bindings = {}) {
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  });
  const exports = {};
  vm.runInNewContext(outputText, { exports, ...bindings });
  return exports;
}

const { hasPermission } = evaluate(await read("lib/permissions.ts"));
const sidebarSource = await read("components/layout/Sidebar.tsx");
const syntax = ts.createSourceFile("Sidebar.tsx", sidebarSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const names = new Set(["desktopSections", "mobileDrawerSections", "isItemActive", "isSidebarItemVisible", "filterSidebarItem"]);
const declarations = syntax.statements.filter((node) =>
  (ts.isVariableStatement(node) && node.declarationList.declarations.some((entry) => names.has(entry.name.getText(syntax)))) ||
  (ts.isFunctionDeclaration(node) && node.name && names.has(node.name.text)),
);
const iconImport = syntax.statements.find((node) =>
  ts.isImportDeclaration(node) && node.moduleSpecifier.text === "lucide-react",
);
const icons = Object.fromEntries(iconImport.importClause.namedBindings.elements.map((item) => [item.name.text, item.name.text]));
const navigation = evaluate(
  declarations.map((node) => node.getText(syntax)).join("\n") +
    "\nexport { desktopSections, mobileDrawerSections, filterSidebarItem, isItemActive };",
  { hasPermission, ...icons },
);

function member({ grants = true, enabled = true } = {}) {
  return {
    role: "manager",
    memberships: [{ business: 1, role: "manager", is_active: true }],
    effective_permissions: { "1": grants ? [{ resource: "ai_assistant", action: "view" }] : [] },
    capabilities: { "1": { modules: { ai: enabled } } },
  };
}

for (const layout of ["desktopSections", "mobileDrawerSections"]) {
  const items = navigation[layout].flatMap((section) => section.items);
  const agent = items.find((item) => item.to === "/app/ai-agents");
  test(`${layout}: one unified agent entry replaces the old assistant`, () => {
    assert.ok(agent);
    const all = items.flatMap(item => [item, ...(item.children || [])]);
    assert.equal(all.filter(item => item.to === "/app/ai-agents").length, 1);
    assert.equal(all.filter(item => item.to === "/app/ai-assistant").length, 0);
  });
  test(`${layout}: existing assistant, analyst and configuration permissions grant navigation`, () => {
    for (const resource of ["ai_assistant", "ai_analyst", "ai_automation"]) {
      const user = member();
      user.effective_permissions["1"] = [{ resource, action: "view" }];
      assert.ok(navigation.filterSidebarItem(agent, user, 1));
    }
  });
  test(`${layout}: missing permission, disabled AI and foreign business hide agents`, () => {
    assert.equal(navigation.filterSidebarItem(agent, member({ grants: false }), 1), null);
    assert.equal(navigation.filterSidebarItem(agent, member({ enabled: false }), 1), null);
    assert.equal(navigation.filterSidebarItem(agent, member(), 2), null);
  });
}

test("old assistant routes redirect into unified agents", async () => {
  const router = await read("app/router.tsx");
  assert.doesNotMatch(router, /AIAssistantPage/);
  assert.match(router, /path: "ai-assistant",[\s\S]*?<Navigate to="\/app\/ai-agents" replace/);
  assert.equal(navigation.isItemActive("/app/ai-agents/12/work", "/app/ai-agents"), true);
});
