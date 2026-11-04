import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";
function harness(initial = [], unavailable = false) {
  const store = new Map(initial), exports = {}, refs = []; let cursor = 0;
  const source = fs.readFileSync(new URL("../../src/features/conversations/hooks/useInboxDraft.ts", import.meta.url), "utf8");
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, {
    exports, require: name => { assert.equal(name, "react"); return { useRef: value => refs[cursor++] ??= { current: value }, useState: value => [value, () => {}] }; },
    sessionStorage: { getItem: key => { if (unavailable) throw Error("blocked"); return store.get(key) ?? null; },
      setItem: (key, value) => { if (unavailable) throw Error("quota"); store.set(key, value); }, removeItem: key => { if (unavailable) throw Error("blocked"); store.delete(key); } },
  });
  return { store, render(user = 202, business = 7, conversation = 88) { cursor = 0; return exports.useInboxDraft(user, business, conversation); } };
}
test("ownerless legacy content is never adopted, including remount and another user", () => {
  const legacy = "zani_inbox_draft:7:88", h = harness([[legacy, "Private draft by unknown author"]]);
  assert.equal(h.render().draft, ""); assert.equal(h.render(303).draft, "");
  assert.equal(harness([...h.store]).render().draft, "");
  assert.deepEqual([...h.store], [[legacy, "Private draft by unknown author"]]);
});
test("current scoped text wins and persists beside ownerless text", () => {
  const h = harness([["zani_inbox_draft:202:7:88", "Own draft"], ["zani_inbox_draft:7:88", "Unproven"]]);
  assert.equal(h.render().draft, "Own draft"); h.render().setDraft(current => current + " edited");
  assert.equal(harness([...h.store]).render().draft, "Own draft edited");
});
test("user, business and conversation switches isolate current drafts", () => {
  const h = harness(); h.render().setDraft("Original");
  for (const ids of [[303,7,88],[202,8,88],[202,7,99]]) { assert.equal(h.render(...ids).draft, ""); h.render(...ids).setDraft(ids.join("/")); }
  assert.equal(h.render().draft, "Original"); assert.equal(harness([...h.store]).render().draft, "Original");
});
test("missing identity never reads or writes", () => {
  const h = harness([["zani_inbox_draft:7:88", "Unproven"]]);
  for (const ids of [[null,7,88],[202,null,88],[202,7,null]]) { const d=h.render(...ids); assert.equal(d.draft, ""); assert.equal(d.draftKey,null); d.setDraft("must not save"); }
  assert.equal(h.store.size,1);
});
test("unavailable storage retains typed in-memory drafts and isolates accounts", () => {
  const h = harness([],true); h.render().setDraft("Memory draft"); assert.equal(h.render().draft,"Memory draft");
  assert.equal(h.render(303).draft,""); assert.equal(h.render().draft,"Memory draft");
});
test("late send does not clear a newer edit or another conversation", () => {
  const h=harness(); let d=h.render(); d.setDraft("Old"); const key=d.draftKey;
  h.render().setDraft("New"); const other=h.render(202,7,99); other.setDraft("Other"); other.clearSentDraft(key,"Old");
  assert.equal(h.render().draft,"New"); assert.equal(h.render(202,7,99).draft,"Other");
});
test("cleared sent draft never resurrects an ownerless legacy value", () => {
  const h=harness([["zani_inbox_draft:7:88","Unproven"]]); let d=h.render(); d.setDraft("Own sent text");
  d=h.render(); d.clearSentDraft(d.draftKey,"Own sent text"); assert.equal(h.render().draft,"");
  assert.equal(harness([...h.store]).render().draft,""); assert.equal(h.store.get("zani_inbox_draft:7:88"),"Unproven");
});
test("empty scoped values do not fall back to legacy content", () => {
  const h=harness([["zani_inbox_draft:202:7:88",""],["zani_inbox_draft:7:88","Unproven"]]); assert.equal(h.render().draft,"");
});
