import { useCallback, useEffect, useRef, useState } from "react";
import { procurementApi as api, type PurchaseContext, type PurchaseFields, type PurchaseRequest, type PurchaseScope, type PurchaseHistory } from "../../api/procurement";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { MedicalRoleCommand, type RoleDraftState, type RoleFormControl } from "../medical/roles/MedicalRoleCommand";
import { medicalRoleDenied } from "../medical/roles/useMedicalRolePage";

const blank: PurchaseFields = { material:"", specification:"", quantity:"", unit:"piece", urgent:false, needed_by:null, comment:"" };
const titleWrap = "[&>header]:h-auto [&>header]:min-h-16 [&>header]:py-3 [&>header>h2]:whitespace-normal";

export function PurchaseEntry({ businessId }: { businessId: number }) {
  const {t} = useI18n();
  const [context,setContext]=useState<PurchaseContext|null>(null);
  const [error,setError]=useState<unknown>(null); const [attempt,setAttempt]=useState(0);
  const [mode,setMode]=useState<"create"|"mine"|null>(null);
  const [draft,setDraft]=useState<RoleDraftState>({dirty:false,pending:false}); const guard=useRef(draft);
  useUnsavedEntryWarning(draft.dirty || draft.pending);
  const denied=useCallback((cause:unknown)=>{setMode(null);setContext(null);setError(cause);setDraft({dirty:false,pending:false});},[]);
  useEffect(()=>{const controller=new AbortController();setContext(null);setError(null);
    void api.context(businessId,controller.signal).then(value=>{if(!controller.signal.aborted)setContext(value);})
      .catch(cause=>{if(!controller.signal.aborted&&!medicalRoleDenied(cause))setError(cause);});
    return ()=>controller.abort();},[businessId,attempt]);
  function close(){if(!guard.current.pending&&(!guard.current.dirty||window.confirm(t("medical.clinical.discard"))))setMode(null);}
  const control:RoleFormControl={guard,onDraft:setDraft,onSaved:()=>setMode(null),onDenied:denied};
  return <div data-testid="purchase-entry" className="space-y-3">
    {error?<ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={()=>setAttempt(n=>n+1)}>{t("common.retry")}</Button>}/>:null}
    {context?.branches.length?<div className="flex flex-wrap gap-2">
      <Button id="purchase-create" size="lg" onClick={()=>setMode("create")}>{t("procurement.create")}</Button>
      <Button id="purchase-mine" size="lg" variant="secondary" onClick={()=>setMode("mine")}>{t("procurement.mine")}</Button>
    </div>:null}
    <Modal open={mode!==null} onClose={close} closeOnBackdrop={false} size="lg" className={titleWrap}
      title={t(mode==="mine"?"procurement.mine":"procurement.create")} focusReturnId={mode==="mine"?"purchase-mine":"purchase-create"}>
      {context&&mode==="create"?<PurchaseForm businessId={businessId} context={context} control={control}/>:null}
      {context&&mode==="mine"?<PurchaseList businessId={businessId} context={context} control={control}/>:null}
    </Modal>
  </div>;
}

export function PurchaseForm({businessId,context,control,item,onResult}: {businessId:number;context:PurchaseContext;control:RoleFormControl;item?:PurchaseRequest;onResult?:()=>void}) {
  const {t}=useI18n();const [fields,setFields]=useState<PurchaseFields>(item?{material:item.material,specification:item.specification,quantity:item.quantity,unit:item.unit,urgent:item.urgent,needed_by:item.needed_by,comment:item.comment}:blank);
  const [branch,setBranch]=useState(String(item?.branch_id??(context.branches.length===1?context.branches[0].id:"")));
  const [reason,setReason]=useState("");
  const change=<K extends keyof PurchaseFields>(key:K,value:PurchaseFields[K])=>setFields(old=>({...old,[key]:value}));
  const valid=Boolean(branch&&fields.material.trim()&&Number(fields.quantity)>0&&(!fields.urgent||fields.needed_by)&&(!item||reason.trim()));
  const payload=valid?{fields,branch,reason}:null;
  return <MedicalRoleCommand payload={payload} dirty={Boolean(item?JSON.stringify(fields)!==JSON.stringify({material:item.material,specification:item.specification,quantity:item.quantity,unit:item.unit,urgent:item.urgent,needed_by:item.needed_by,comment:item.comment})||reason:JSON.stringify(fields)!==JSON.stringify(blank))}
    label={t(item?"common.save":"procurement.submit")} control={control} submit={async(value,key)=>{
      const scope={business_id:businessId,branch_id:Number(value.branch)};
      if(item)await api.change(scope,item,"edit",value.reason,value.fields,key);else await api.create(scope,value.fields,key);
      onResult?.();
    }}>
    <Select label={t("medical.branch")} value={branch} disabled={!!item} options={[{value:"",label:t("medical.reception.chooseOption")},...context.branches.map(row=>({value:row.id,label:row.name}))]} onChange={event=>setBranch(event.target.value)}/>
    <Input label={t("procurement.material")} required maxLength={200} value={fields.material} onChange={event=>change("material",event.target.value)}/>
    <Input label={t("procurement.specification")} maxLength={200} value={fields.specification} onChange={event=>change("specification",event.target.value)}/>
    <div className="grid min-w-0 gap-4 sm:grid-cols-2">
      <Input label={t("procurement.quantity")} type="number" min={fields.unit==="piece"||fields.unit==="package"?"1":"0.001"} step={fields.unit==="piece"||fields.unit==="package"?"1":"0.001"} required value={fields.quantity} onChange={event=>change("quantity",event.target.value)}/>
      <Select label={t("procurement.unit")} value={fields.unit} options={["piece","package","ml","l","g","kg","m"].map(unit=>({value:unit,label:t(`procurement.unit.${unit}`)}))} onChange={event=>change("unit",event.target.value)}/>
      <Select label={t("procurement.priority")} value={fields.urgent?"urgent":"planned"} options={[{value:"planned",label:t("procurement.planned")},{value:"urgent",label:t("procurement.urgent")}]} onChange={event=>change("urgent",event.target.value==="urgent")}/>
      <Input label={t("procurement.neededBy")} type="date" required={fields.urgent} value={fields.needed_by??""} onChange={event=>change("needed_by",event.target.value||null)}/>
    </div>
    <Textarea label={t("procurement.comment")} maxLength={1000} value={fields.comment} onChange={event=>change("comment",event.target.value)}/>
    {item?<Textarea label={t("procurement.reason")} required maxLength={1000} value={reason} onChange={event=>setReason(event.target.value)}/>:null}
    <Button type="button" variant="secondary" onClick={()=>{if(!control.guard.current.dirty||window.confirm(t("medical.clinical.discard")))control.onSaved();}}>{t("common.cancel")}</Button>
  </MedicalRoleCommand>;
}

function PurchaseList({businessId,context,control}:{businessId:number;context:PurchaseContext;control:RoleFormControl}) {
  const {t}=useI18n();const [branch,setBranch]=useState(String(context.branches.length===1?context.branches[0].id:""));
  const [rows,setRows]=useState<PurchaseRequest[]>([]);const [next,setNext]=useState<number|null>(null);
  const [loading,setLoading]=useState(false);const [error,setError]=useState<unknown>(null);
  const [selected,setSelected]=useState<PurchaseRequest|null>(null);const [action,setAction]=useState<"edit"|"cancel"|null>(null);
  const [reason,setReason]=useState("");const active=useRef<AbortController|null>(null);
  const scope={business_id:businessId,branch_id:Number(branch)};
  async function load(after=0){active.current?.abort();const controller=new AbortController();active.current=controller;setLoading(true);setError(null);
    try{const page=await api.list(scope,after,controller.signal);if(!controller.signal.aborted){setRows(old=>after?[...old,...page.results]:page.results);setNext(page.next_id);}}
    catch(cause){if(!controller.signal.aborted){if(medicalRoleDenied(cause))control.onDenied(cause);else setError(cause);}}
    finally{if(!controller.signal.aborted)setLoading(false);}}
  useEffect(()=>{setRows([]);setSelected(null);if(branch)void load();return()=>active.current?.abort();},[businessId,branch]);
  const finish=()=>{setAction(null);setSelected(null);setReason("");void load();};
  const localControl={...control,onSaved:finish};
  if(selected&&action==="edit")return <PurchaseForm businessId={businessId} context={context} item={selected} control={localControl}/>;
  if(selected&&action==="cancel")return <MedicalRoleCommand payload={reason.trim()?{reason}:null} dirty={!!reason} label={t("procurement.cancelRequest")} control={localControl}
    submit={(value,key)=>api.change(scope,selected,"cancel",value.reason,undefined,key)}>
    <p className="break-words font-medium">{selected.material}</p><Textarea label={t("procurement.reason")} maxLength={1000} required value={reason} onChange={event=>setReason(event.target.value)}/>
  </MedicalRoleCommand>;
  return <div className="space-y-4">
    <Select label={t("medical.branch")} value={branch} options={[{value:"",label:t("medical.reception.chooseOption")},...context.branches.map(row=>({value:row.id,label:row.name}))]} onChange={event=>setBranch(event.target.value)}/>
    {loading?<LoadingState/>:null}{error?<ErrorState message={getApiErrorMessage(error)} action={<Button variant="secondary" onClick={()=>void load()}>{t("common.retry")}</Button>}/>:null}
    {!loading&&!error&&branch&&!rows.length?<p>{t("procurement.empty")}</p>:null}
    {rows.map(item=><section key={item.id} className="space-y-3 rounded-card border border-platforma-border p-4" data-testid={`purchase-request-${item.id}`}>
      <h3 className="break-words font-semibold">{item.material}</h3><p className="break-words text-sm">{item.specification}</p>
      <p>{item.quantity} {t(`procurement.unit.${item.unit}`)} · {t(`procurement.state.${item.state}`)}</p>
      <p>{t(item.urgent?"procurement.urgent":"procurement.planned")}{item.needed_by?` · ${item.needed_by}`:""}</p>
      {item.state==="new"?<div className="flex flex-wrap gap-2"><Button variant="secondary" onClick={()=>{setSelected(item);setAction("edit");}}>{t("common.edit")}</Button><Button variant="secondary" onClick={()=>{setSelected(item);setAction("cancel");}}>{t("procurement.cancelRequest")}</Button></div>:null}
      <PurchaseHistoryPanel scope={scope} item={item} onDenied={control.onDenied}/>
    </section>)}
    {next!==null?<Button variant="secondary" disabled={loading} onClick={()=>void load(next)}>{t("medical.templates.more")}</Button>:null}
  </div>;
}

function PurchaseHistoryPanel({scope,item,onDenied}:{scope:PurchaseScope;item:PurchaseRequest;onDenied:(cause:unknown)=>void}) {
  const {t,language}=useI18n();const [rows,setRows]=useState<PurchaseHistory[]>([]);const [next,setNext]=useState<number|null>(null);const [error,setError]=useState<unknown>(null);const [busy,setBusy]=useState(false);
  async function load(after=0){setBusy(true);setError(null);try{const page=await api.history(scope,item.id,after);setRows(old=>after?[...old,...page.results]:page.results);setNext(page.next_id);}catch(cause){if(medicalRoleDenied(cause))onDenied(cause);else setError(cause);}finally{setBusy(false);}}
  return <details onToggle={event=>{if(event.currentTarget.open&&!rows.length&&!busy)void load();}}><summary className="min-h-11 cursor-pointer py-3">{t("procurement.history")}</summary>
    {busy?<LoadingState/>:null}{error?<ErrorState message={getApiErrorMessage(error)} action={<Button onClick={()=>void load()}>{t("common.retry")}</Button>}/>:null}
    <ol className="space-y-3">{rows.map(row=><li key={row.id} className="break-words text-sm"><p>{row.actor_name} · {t(`procurement.history.${row.action}`)}</p><p>{new Date(row.created_at).toLocaleString(language)}</p><p>{row.snapshot.material} · {row.snapshot.quantity} {t(`procurement.unit.${row.snapshot.unit}`)}</p>{row.reason?<p>{row.reason}</p>:null}</li>)}</ol>
    {next!==null?<Button variant="secondary" disabled={busy} onClick={()=>void load(next)}>{t("medical.templates.more")}</Button>:null}
  </details>;
}
