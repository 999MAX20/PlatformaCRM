import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import ts from 'typescript';
function harness() {
 const refs=[], mutations=[], calls=[], cleared=[], notices=[], errors=[];let cursor=0;
 const api={sendMessage:async p=>p,retryMessage:async p=>p};
 const imports={react:{useRef:value=>refs[cursor++]??={current:value}},'@tanstack/react-query':{useMutation:options=>{const value={...options,isPending:false,mutate:payload=>calls.push(payload)};mutations.push(value);return value;}},'../../api/inbox':{inboxApi:api},'./inboxIdempotency':{createIdempotencyKey:scope=>scope+':'+(calls.length+1)}};
 const source=fs.readFileSync(new URL('../../src/features/conversations/useInboxSending.ts',import.meta.url),'utf8');const exports={};
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{exports,require:name=>{assert.ok(imports[name],name);return imports[name];}});
 const args={selected:{id:11,status:'open'},draft:' hello ',draftKey:'u:1:b:2:c:11',canUpdate:true,clearSentDraft:(...x)=>cleared.push(x),currentConversationRef:{current:11},setSuggestedReply:x=>calls.push({suggestion:x}),setNotice:(...x)=>notices.push(x),t:x=>x,invalidateInbox:async()=>{},notifyError:(...x)=>errors.push(x),composerRef:{current:null}};
 return {calls,cleared,notices,errors,args,render(overrides={}){cursor=0;mutations.length=0;return exports.useInboxSending({...args,...overrides});}};
}
test('failed sends retain draft and reuse the key for the same text; changed text gets a new key',()=>{
 const h=harness();let m=h.render();m.sendReply();const first=h.calls[0];m.sendMutation.onError(new Error('offline'));assert.equal(h.cleared.length,0);
 m=h.render();m.sendReply();assert.equal(h.calls[1].idempotencyKey,first.idempotencyKey);assert.equal(h.calls[1].text,'hello');
 h.render({draft:'changed'}).sendReply();assert.notEqual(h.calls[2].idempotencyKey,first.idempotencyKey);assert.equal(h.errors.length,1);
});
test('late successful send clears only its captured draft and does not replace another conversation suggestion',async()=>{
 const h=harness();const m=h.render();m.sendReply();const sent=h.calls[0];h.args.currentConversationRef.current=22;
 await m.sendMutation.onSuccess({status:'delivery_unknown'},sent);
 assert.deepEqual(h.cleared,[[sent.draftKey,sent.text]]);assert.equal(h.calls.length,1);assert.equal(h.notices[0][1],'warning');
});
test('empty, closed, forbidden and pending sends do not dispatch',()=>{
 const h=harness();for(const args of [{draft:' '},{selected:null},{selected:{id:11,status:'closed'}},{canUpdate:false}])h.render(args).sendReply();
 const m=h.render();m.sendMutation.isPending=true;m.sendReply();assert.equal(h.calls.length,0);
});
test('uncertain retry keeps the message key until successful completion',async()=>{
 const h=harness();let m=h.render();m.retryMessage(4);const first=h.calls[0];m.retryMessageMutation.onError(new Error('timeout'));
 m=h.render();m.retryMessage(4);assert.equal(h.calls[1].idempotencyKey,first.idempotencyKey);assert.equal(h.calls[1].messageId,4);
 await m.retryMessageMutation.onSuccess({},h.calls[1]);h.render().retryMessage(4);assert.notEqual(h.calls[2].idempotencyKey,first.idempotencyKey);
});
