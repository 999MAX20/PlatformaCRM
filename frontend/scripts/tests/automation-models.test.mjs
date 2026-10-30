import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};
function harness(api) {
  const state = [], effects = [], invalidated = [];
  let cursor = 0;
  const imports = {
    react: {
      useState(initial) {
        const i = cursor++;
        if (!(i in state)) state[i] = typeof initial === "function" ? initial() : initial;
        return [state[i], next => { state[i] = typeof next === "function" ? next(state[i]) : next; }];
      },
      useRef(initial) { const i = cursor++; return state[i] ??= { current: initial }; },
      useEffect(effect, deps) {
        const i = cursor++;
        if (!state[i] || deps.some((value, n) => value !== state[i][n])) { state[i] = deps; effects.push(effect); }
      },
    },
    "@tanstack/react-query": {
      useQuery: () => ({ data: [] }),
      useQueryClient: () => ({ invalidateQueries: value => invalidated.push(value) }),
      useMutation: options => ({ isPending: false, async mutateAsync(value) {
        try { const result = await options.mutationFn(value); await options.onSuccess?.(result, value); return result; }
        catch (error) { await options.onError?.(error, value); throw error; }
      } }),
    },
    "../../api/automations": { automationRulesApi: api, automationActionErrors: () => ({}) },
    "../../api/team": { teamApi: { allMembers: async () => [] } },
    "../../api/client": { getApiErrorMessage: error => error.message },
    "../../lib/i18n": { useI18n: () => ({ t: key => key }) },
  };
  function load(name) {
    if (imports[name]) return imports[name];
    assert.ok(["./automationPresentation", "./editorDraft", "./useAutomationEditor"].includes(name), name);
    const source = fs.readFileSync(new URL(`../../src/features/automations/${name.slice(2)}.ts`, import.meta.url), "utf8");
    const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
    const exports = {};
    vm.runInNewContext(compiled, { exports, require: load, structuredClone });
    return imports[name] = exports;
  }
  const { useAutomationEditor } = load("./useAutomationEditor");
  function render(id = 7) {
    cursor = 0;
    const result = useAutomationEditor({ id }, true);
    if (effects.length) { effects.splice(0).forEach(effect => effect()); return render(id); }
    return result;
  }
  return { render, invalidated };
}
const rule = (id, name) => ({ id, business: 7, name, trigger_type: "lead_created", description: "", is_active: false, priority: 100, conditions: [], actions: [] });

test("editor ignores an older rule response after a different rule is selected", async () => {
  const first = deferred(), second = deferred();
  const h = harness({ get: id => id === 1 ? first.promise : second.promise });
  const one = h.render().openEditor(1);
  const two = h.render().openEditor(2);
  second.resolve(rule(2, "Second")); await two;
  first.resolve(rule(1, "First")); await one;
  assert.equal(h.render().advancedForm.name, "Second");
  assert.equal(h.render().editingRuleId, 2);
  assert.equal(h.render().editorLoading, false);
});

test("closing editor ignores an in-flight preview", async () => {
  const response = deferred(), h = harness({ previewManual: () => response.promise });
  await h.render().openEditor();
  const model = h.render();
  const pending = model.previewMutation.mutateAsync({ id: null, payload: model.buildManualPayload(), signature: model.draftSignature, session: model.editorSession.current });
  model.closeEditor(); response.resolve({ ok: true }); await pending;
  assert.equal(h.render().advancedOpen, false);
  assert.equal(h.render().preview, null);
});

test("Business switch invalidates an in-flight editor read", async () => {
  const response = deferred(), h = harness({ get: () => response.promise });
  const pending = h.render().openEditor(1);
  h.render(8); response.resolve(rule(1, "Previous Business")); await pending;
  assert.equal(h.render(8).advancedOpen, false);
  assert.equal(h.render(8).advancedForm.name, "");
});

test("editing reviewed input invalidates preview; saving refreshes rules", async () => {
  const h = harness({ previewManual: async () => ({ ok: true }), createManual: async payload => payload });
  await h.render().openEditor();
  let model = h.render();
  await model.previewMutation.mutateAsync({ id: null, payload: model.buildManualPayload(), signature: model.draftSignature, session: model.editorSession.current });
  model = h.render(); assert.equal(model.validPreview.ok, true);
  model.setAdvancedForm({ ...model.advancedForm, name: "Changed" });
  model = h.render(); assert.equal(model.validPreview, null);
  await model.createManualMutation.mutateAsync({ id: null, payload: model.buildManualPayload(), session: model.editorSession.current });
  assert.equal(h.render().advancedOpen, false);
  assert.equal(h.invalidated[0].queryKey[0], "automation-rules");
});
