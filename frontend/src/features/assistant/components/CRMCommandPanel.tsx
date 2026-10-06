import { LoadingState } from "../../../components/ui/StateViews";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { aiApi } from "../../../api/ai";
import { aiCRMApi, type CRMEntity, type CRMRecord } from "../../../api/aiCRM";
import { getApiErrorMessage } from "../../../api/client";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { Card, CardBody } from "../../../components/ui/Card";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { Textarea } from "../../../components/ui/Textarea";
import { useI18n } from "../../../lib/i18n";
import type { AIToolCallLog, Id } from "../../../types";

const entities: CRMEntity[] = ["clients", "leads", "deals", "tasks", "appointments"];
const routeKeys = { clients: "client", leads: "lead", deals: "deal", tasks: "task", appointments: "appointment" };
const routePaths = { clients: "clients", leads: "leads", deals: "deals", tasks: "tasks", appointments: "calendar" };
function label(row: CRMRecord) { return row.full_name || row.title || row.message || row.start_at || `#${row.id}`; }
function text(value: unknown) { return value === null || value === undefined || value === "" ? "—" : String(value); }

export function CRMCommandPanel({ businessId, agentId, allowedSources = entities, canSuggest, canExecute }: { businessId: Id; agentId?: Id; allowedSources?: CRMEntity[]; canSuggest: boolean; canExecute: boolean }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const confirm = useActionConfirm();
  const [entity, setEntity] = useState<CRMEntity>(allowedSources[0] || "clients");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [archived, setArchived] = useState(false);
  const [target, setTarget] = useState<CRMRecord | null>(null);
  const [message, setMessage] = useState("");
  const [proposal, setProposal] = useState<AIToolCallLog | null>(null);
  const approvals = useRef(new Map<Id, Id>());
  const records = useQuery({ queryKey: ["ai-crm-records", businessId, agentId, entity, query, offset, archived],
    queryFn: () => aiCRMApi.read({ business: businessId, agent: agentId, entity, query, offset, include_archived: archived }) });
  const plan = useMutation({ mutationFn: () => aiCRMApi.plan({ business: businessId, agent: agentId, entity, entity_id: target?.id, message }),
    onMutate: () => setProposal(null), onSuccess: result => setProposal(result.suggested_actions[0] || null) });
  const execute = useMutation({ mutationFn: async (action: AIToolCallLog) => {
    let approvalId = approvals.current.get(action.id);
    if (!approvalId) {
      const approval = await aiApi.createToolApproval({ business: businessId, toolCallId: action.id });
      approvalId = approval.id;
      approvals.current.set(action.id, approvalId);
    }
    const saved = await aiApi.getToolApproval(approvalId);
    if (saved.status === "pending") await aiApi.approveToolApproval({ id: approvalId });
    return aiApi.executeTool(action.id, approvalId);
  }, onSuccess: async result => {
    setProposal(result);
    const record = result.output_json.record as CRMRecord | undefined;
    if (record && typeof record.id === "number") setTarget(record);
    await Promise.all(["ai-crm-records", "ai-history", "clients", "leads", "deals", "tasks", "appointments", "activity-events", "notifications"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
  } });
  const busy = plan.isPending || execute.isPending;
  const clear = () => { setProposal(null); plan.reset(); execute.reset(); };
  const fields = proposal?.input_json.values && typeof proposal.input_json.values === "object" ? proposal.input_json.values as Record<string, unknown> : {};
  const before = proposal?.input_json.before && typeof proposal.input_json.before === "object" ? proposal.input_json.before as Record<string, unknown> : {};
  return <Card aria-label={t("aiCRM.title")}><CardBody className="space-y-4">
    <h2 className="text-lg font-semibold">{t("aiCRM.title")}</h2>
    <div className="grid gap-3 sm:grid-cols-2">
      <Select label={t("aiCRM.entity")} value={entity} disabled={busy} onChange={event => { setEntity(event.target.value as CRMEntity); setTarget(null); setOffset(0); clear(); }} options={allowedSources.map(value => ({ value, label: t(`aiWorkflow.source.${value}`) }))} />
      <Input label={t("common.search")} value={query} disabled={busy} onChange={event => { setQuery(event.target.value); setOffset(0); setTarget(null); clear(); }} />
    </div>
    <label className="flex min-h-9 items-center gap-2 text-sm"><input type="checkbox" checked={archived} disabled={busy} onChange={event => { setArchived(event.target.checked); setOffset(0); setTarget(null); clear(); }} />{t("aiCRM.includeArchived")}</label>
    {records.isLoading && <LoadingState />}
    {records.error && <div role="alert"><p>{getApiErrorMessage(records.error)}</p><Button variant="secondary" onClick={() => records.refetch()}>{t("aiCRM.retry")}</Button></div>}
    {records.data && <>
      <Select label={t("aiCRM.target")} value={target ? String(target.id) : ""} disabled={busy} onChange={event => { setTarget(records.data.results.find(row => row.id === Number(event.target.value)) || null); clear(); }} options={[{ value: "", label: t("aiCRM.newRecord") }, ...records.data.results.map(row => ({ value: String(row.id), label: `${label(row)} · #${row.id}` }))]} />
      <div className="flex flex-wrap items-center gap-3 text-sm"><span>{t("aiCRM.found", { count: records.data.count })}</span><Button size="sm" variant="ghost" disabled={!offset || busy} onClick={() => { setOffset(Math.max(0, offset - 20)); setTarget(null); clear(); }}>{t("aiCRM.previous")}</Button><Button size="sm" variant="ghost" disabled={!records.data.has_more || busy} onClick={() => { setOffset(offset + 20); setTarget(null); clear(); }}>{t("aiCRM.next")}</Button></div>
    </>}
    {target && <div className="rounded-xl border border-platforma-border p-3 text-sm">
      <Link className="underline" to={`/app/${routePaths[entity]}?${routeKeys[entity]}=${target.id}`}>{label(target)}</Link>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2">{Object.entries(target).filter(([key, value]) => ["phone", "email", "title", "message", "description", "start_at", "due_at", "amount", "notes"].includes(key) && value !== null && value !== "").map(([key, value]) => <div key={key} className="min-w-0"><dt className="text-platforma-subtle">{t(`aiCRM.field.${key}`)}</dt><dd className="break-words">{text(value)}</dd></div>)}</dl>
    </div>}
    <form className="space-y-3" onSubmit={event => { event.preventDefault(); plan.mutate(); }}>
      <Textarea label={t("aiCRM.request")} value={message} disabled={busy || !canSuggest} onChange={event => { setMessage(event.target.value); clear(); }} />
      <Button type="submit" variant="ai" disabled={!canSuggest || !message.trim() || records.isError} isLoading={plan.isPending}>{t("aiCRM.prepare")}</Button>
    </form>
    {(plan.error || execute.error) && <p role="alert" className="text-sm text-platforma-danger">{getApiErrorMessage(plan.error || execute.error)}</p>}
    {plan.data?.question && <p role="status">{plan.data.question}</p>}
    {proposal && <section aria-label={t("aiCRM.review")} className="space-y-3 rounded-xl border border-platforma-border p-4">
      <h3 className="font-semibold">{t(`aiWorkflow.tool.${proposal.tool_name}`)}{proposal.input_json.action ? ` · ${t(`aiCRM.action.${proposal.input_json.action}`)}` : ""}</h3>
      {Object.keys(fields).length > 0 && <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">{t("aiCRM.field")}</th><th className="p-2">{t("aiCRM.before")}</th><th className="p-2">{t("aiCRM.after")}</th></tr></thead><tbody>{Object.entries(fields).map(([key, value]) => <tr key={key}><th className="p-2 font-medium">{t(`aiCRM.field.${key}`)}</th><td className="p-2 break-words">{text(before[key])}</td><td className="p-2 break-words">{text(value)}</td></tr>)}</tbody></table></div>}
      {proposal.input_json.reason ? <p className="text-sm">{text(proposal.input_json.reason)}</p> : null}
      {proposal.status === "executed" ? <p role="status" className="text-platforma-success">{t("aiCRM.executed")}</p> : <div className="flex flex-wrap gap-2">
        <Button disabled={!canExecute || proposal.status !== "suggested"} isLoading={execute.isPending} onClick={async () => {
          const result = await confirm({ title: t("aiCRM.confirmTitle"), description: t("aiCRM.confirmText"), confirmLabel: t("actions.confirm"), tone: proposal.tool_name === "crm_archive" ? "danger" : "ai" });
          if (result.confirmed) execute.mutate(proposal);
        }}>{t("actions.confirm")}</Button>
        <Button variant="secondary" disabled={busy} onClick={clear}>{t("aiCRM.discard")}</Button>
      </div>}
    </section>}
  </CardBody></Card>;
}
