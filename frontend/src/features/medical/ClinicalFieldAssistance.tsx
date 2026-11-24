import {useEffect,useRef,useState} from "react";
import {medicalAssistanceApi as api,type AssistanceScope,type AssistanceSuggestion} from "../../api/medicalAssistance";
import {Button} from "../../components/ui/Button";
import {useI18n} from "../../lib/i18n";
import {medicalRoleDenied} from "./roles/useMedicalRolePage";
import {useVoiceRecorder} from "../voice/useVoiceRecorder";

export function ClinicalFieldAssistance({scope,text,disabled,onAccept,onDenied,onBusy}:{scope:AssistanceScope;text:string;disabled:boolean;onAccept:(text:string)=>void;onDenied:(cause:unknown)=>void;onBusy?:(busy:boolean)=>void}){
 const {t,language}=useI18n();const [suggestion,setSuggestion]=useState<AssistanceSuggestion|null>(null);
 const recorder=useVoiceRecorder();const recording=recorder.state!=="idle";
 const [pending,setPending]=useState(false);const [failed,setFailed]=useState(false);
 const current=useRef({text,scope,disabled,onAccept});current.current={text,scope,disabled,onAccept};
 const active=useRef<AbortController|null>(null);const input=useRef("");
 const preview=useRef<HTMLDivElement>(null);const requestButton=useRef<HTMLButtonElement>(null);
 const scopeKey=JSON.stringify(scope);
 useEffect(()=>{onBusy?.(pending||recording);},[pending,recording,onBusy]);
 useEffect(()=>()=>onBusy?.(false),[onBusy]);
 useEffect(()=>{active.current?.abort();recorder.cancel();setSuggestion(null);setFailed(false);setPending(false);return()=>active.current?.abort();},[scopeKey,text,disabled,recorder.cancel]);
 useEffect(()=>{const cancelOther=(event:Event)=>{if((event as CustomEvent<string>).detail!==scopeKey)recorder.cancel();};window.addEventListener("platforma:clinical-dictation",cancelOther);return()=>window.removeEventListener("platforma:clinical-dictation",cancelOther);},[scopeKey,recorder.cancel]);
 function dismiss(){active.current?.abort();setSuggestion(null);setFailed(false);setPending(false);requestButton.current?.focus();}
 async function request(){if(disabled||pending||!text.trim())return;
  const controller=new AbortController();active.current=controller;input.current=text;setPending(true);setFailed(false);setSuggestion(null);
  try{const result=await api.suggest(scope,text,controller.signal);
   if(!controller.signal.aborted&&current.current.text===text&&JSON.stringify(current.current.scope)===scopeKey&&!current.current.disabled){
    setSuggestion(result);if(document.activeElement===requestButton.current)requestAnimationFrame(()=>preview.current?.focus());
   }}catch(cause){if(!controller.signal.aborted){if(medicalRoleDenied(cause))onDenied(cause);else setFailed(true);}}
  finally{if(!controller.signal.aborted)setPending(false);}
 }
 async function accept(){if(!suggestion||pending||disabled||current.current.text!==input.current)return;
  const controller=new AbortController();active.current=controller;setPending(true);setFailed(false);
  try{const result=await api.accept(scope,input.current,suggestion,controller.signal);
   if(!controller.signal.aborted&&current.current.text===input.current&&JSON.stringify(current.current.scope)===scopeKey&&!current.current.disabled){current.current.onAccept(result.text);setSuggestion(null);requestButton.current?.focus();}
  }catch(cause){if(!controller.signal.aborted){setSuggestion(null);if(medicalRoleDenied(cause))onDenied(cause);else setFailed(true);}}
  finally{if(!controller.signal.aborted)setPending(false);}
 }
 async function stopDictation(){
  const original=input.current;const capturedScope=scopeKey;const audio=await recorder.stop();
  if(!audio||current.current.disabled||current.current.text!==original||JSON.stringify(current.current.scope)!==capturedScope)return;
  const controller=new AbortController();active.current=controller;setPending(true);setFailed(false);
  try{const result=await api.dictate(scope,original,audio,language==="kk"?"kk":"ru",controller.signal);
   if(!controller.signal.aborted&&current.current.text===original&&JSON.stringify(current.current.scope)===capturedScope)setSuggestion(result);
  }catch(cause){if(!controller.signal.aborted){if(medicalRoleDenied(cause))onDenied(cause);else setFailed(true);}}
  finally{if(!controller.signal.aborted)setPending(false);}
 }
 recorder.limitCallback.current=()=>void stopDictation();
 return <div className="space-y-2" data-testid={`clinical-assistance-${scope.field}`}>
  <div className="flex flex-wrap gap-2">
   <Button size="lg" ref={requestButton} type="button" variant="secondary" disabled={disabled||pending||recording||!text.trim()||text.length>8000} isLoading={pending} onClick={()=>void request()}>{t("medical.assistance.format")}</Button>
   {recording?<><Button size="lg" type="button" disabled={recorder.state!=="recording"} onClick={()=>void stopDictation()}>{t("medical.assistance.stopSeconds",{seconds:Math.floor(recorder.seconds)})}</Button><Button size="lg" type="button" variant="secondary" onClick={recorder.cancel}>{t("common.cancel")}</Button></>:<Button size="lg" type="button" variant="secondary" disabled={disabled||pending||text.length>8000} onClick={()=>{input.current=text;setSuggestion(null);setFailed(false);window.dispatchEvent(new CustomEvent("platforma:clinical-dictation",{detail:scopeKey}));void recorder.start("");}}>{t("medical.assistance.dictate")}</Button>}
  </div>
  {recorder.error?<p role="status" className="text-sm text-platforma-subtle">{t("medical.assistance.microphoneUnavailable")}</p>:null}
  {failed?<p role="status" className="text-sm text-platforma-subtle">{t("medical.assistance.unavailable")}</p>:null}
  {suggestion?<div ref={preview} tabIndex={0} role="region" aria-label={t("medical.assistance.preview")} className="platforma-focus-ring space-y-3 rounded-card border border-platforma-border p-3"
   onKeyDown={event=>{if(event.key==="Escape"){event.preventDefault();event.stopPropagation();dismiss();}else if(event.key==="Tab"&&!event.shiftKey&&event.target===event.currentTarget){event.preventDefault();void accept();}}}>
   <p className="text-sm font-medium">{t("medical.assistance.preview")}</p><p className="whitespace-pre-wrap break-words text-sm">{suggestion.text}</p>
   <div className="flex flex-wrap gap-2"><Button size="lg" type="button" disabled={pending} onClick={()=>void accept()}>{t("medical.assistance.accept")}</Button><Button size="lg" type="button" variant="secondary" disabled={pending} onClick={dismiss}>{t("medical.assistance.dismiss")}</Button></div>
  </div>:null}
 </div>;
}
