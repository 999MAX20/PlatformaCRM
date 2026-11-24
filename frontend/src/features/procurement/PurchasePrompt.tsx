import {useEffect,useRef,useState} from "react";
import {medicalPurchasePromptApi as api,type PurchasePromptScope} from "../../api/medicalPurchasePrompt";
import {getApiErrorMessage} from "../../api/client";
import {Modal} from "../../components/ui/Modal";
import {Button} from "../../components/ui/Button";
import {ErrorState} from "../../components/ui/StateViews";
import {useI18n} from "../../lib/i18n";
import {useActiveBusiness} from "../../hooks/useBusiness";
import {useAuth} from "../auth/AuthProvider";
import {useUnsavedEntryWarning} from "../auth/useUnsavedEntryWarning";
import {medicalRoleDenied} from "../medical/roles/useMedicalRolePage";
import type {RoleDraftState} from "../medical/roles/MedicalRoleCommand";
import {PurchaseForm} from "./PurchaseEntry";

const eventName="platforma:completed-encounter-left";
export function offerPurchaseAfterCompletion(scope:PurchasePromptScope){
 window.dispatchEvent(new CustomEvent(eventName,{detail:scope}));
}

export function PurchasePrompt(){
 const {t}=useI18n();const {business}=useActiveBusiness();const {user}=useAuth();
 const [offer,setOffer]=useState<{businessId:number;token:string;branch:{id:number;name:string}}|null>(null);
 const [form,setForm]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState<unknown>(null);
 const [draft,setDraft]=useState<RoleDraftState>({dirty:false,pending:false});const guard=useRef(draft);
 const inFlight=useRef(false);useUnsavedEntryWarning(draft.dirty||draft.pending);
 useEffect(()=>{const controller=new AbortController();setOffer(null);setForm(false);setError(null);setDraft({dirty:false,pending:false});
  const receive=(event:Event)=>{const scope=(event as CustomEvent<PurchasePromptScope>).detail;
   if(scope.business_id!==Number(business?.id)||inFlight.current)return;
   inFlight.current=true;
   void api.claim(scope,controller.signal).then(value=>{if(!controller.signal.aborted&&value.show&&value.token&&value.branch){
    setOffer({businessId:scope.business_id,token:value.token,branch:value.branch});
   }}).catch(()=>{/* Optional prompt failure never changes the completed visit. */}).finally(()=>{inFlight.current=false;});
  };
  window.addEventListener(eventName,receive);return()=>{controller.abort();window.removeEventListener(eventName,receive);};
 },[business?.id,user?.id]);
 useEffect(()=>{if(offer)void api.decide(offer.businessId,offer.token,"ack").catch(()=>{});},[offer]);
 async function decide(value:"yes"|"no"){
  if(!offer||busy)return;setBusy(true);setError(null);
  try{await api.decide(offer.businessId,offer.token,value);if(value==="yes")setForm(true);else setOffer(null);}
  catch(cause){if(medicalRoleDenied(cause)){setOffer(null);setForm(false);}else setError(cause);}
  finally{setBusy(false);}
 }
 function close(){if(busy||guard.current.pending)return;if(!form){void decide("no");return;}
  if(!guard.current.dirty||window.confirm(t("medical.clinical.discard"))){setOffer(null);setForm(false);}}
 return <Modal open={!!offer} onClose={close} closeOnBackdrop={false} size={form?"lg":"sm"}
  title={t(form?"procurement.create":"procurement.prompt.title")} className="[&>header]:h-auto [&>header]:min-h-16 [&>header]:py-3 [&>header>h2]:whitespace-normal">
  {offer&&form?<PurchaseForm businessId={offer.businessId} context={{branches:[offer.branch]}} control={{guard,onDraft:setDraft,onSaved:()=>{setOffer(null);setForm(false);},onDenied:()=>{setOffer(null);setForm(false);}}}/>:offer?<div className="space-y-4">
   <p>{t("procurement.prompt.body")}</p>{error?<ErrorState message={getApiErrorMessage(error)}/>:null}
   <div className="flex flex-wrap gap-2"><Button size="lg" disabled={busy} onClick={()=>void decide("yes")}>{t("procurement.prompt.yes")}</Button><Button size="lg" variant="secondary" disabled={busy} onClick={()=>void decide("no")}>{t("procurement.prompt.no")}</Button></div>
  </div>:null}
 </Modal>;
}
