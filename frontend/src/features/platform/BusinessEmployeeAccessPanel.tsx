import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { employeeAccessApi, type AccessAction, type AccessRepair, type AccessTerms } from "../../api/employeeAccess";
import { issueMfaStepUp } from "../../api/auth";
import { normalizeAppError } from "../../api/appError";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { EmployeeAccessSummary } from "../account/EmployeeAccessSummary";
import { PlatformLoadError } from "./PlatformData";
import { SupportCreateDialog } from "../support/SupportCreateDialog";
import { retainSupportData } from "../support/SupportUI";
import { ClinicPager } from "./ClinicReadUI";
import { EmployeeAccessDiagnostics, type AccessTarget } from "./EmployeeAccessDiagnostics";

type Props = { business: string; params: URLSearchParams; update: (values: Record<string, string>) => void; onDraft: (value: { dirty: boolean; pending: boolean }) => void };
export function BusinessEmployeeAccessPanel({ business, params, update, onDraft }: Props) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const kind = params.get("access_kind") === "invitation" ? "invitation" : "member";
  const search = params.get("access_search") || "";
  const page = Math.max(1, Math.floor(Number(params.get("access_page")) || 1));
  const [searchDraft, setSearchDraft] = useState(search);
  const [target, setTarget] = useState<AccessTarget | null>(null);
  const [action, setAction] = useState<AccessAction | "">("");
  const [role, setRole] = useState("");
  const [caseId, setCaseId] = useState("");
  const [reason, setReason] = useState("");
  const [mfa, setMfa] = useState("");
  const [creatingCase, setCreatingCase] = useState(false);
  const retryTerms = useRef<AccessTerms | null>(null);
  const query = useQuery({ queryKey: ["platform-employee-access", business, search, page], queryFn: () => employeeAccessApi.get(business, { search, page }), retry: false, gcTime: 0, refetchOnWindowFocus: false });
  const hasTerms = Boolean(target || caseId || reason || role);
  const dirty = hasTerms || Boolean(mfa);
  function clear() { setTarget(null); setAction(""); setRole(""); setCaseId(""); setReason(""); setMfa(""); retryTerms.current = null; }
  const mutation = useMutation({ mutationFn: async (command: { type: "prepare" } | { type: "execute" | "cancel"; item: AccessRepair }) => {
    const token = (await issueMfaStepUp(mfa)).step_up_token;
    if (command.type !== "prepare") return employeeAccessApi.act(business, command.item.id, command.type, token);
    const terms: AccessTerms = { request_id: retryTerms.current?.request_id || crypto.randomUUID(), action: action as AccessAction,
      target_id: target!.row.id, target_role_id: action === "role" ? Number(role) : null,
      expected_revision: target!.row.revision, support_case_id: Number(caseId), reason: reason.trim() };
    if (retryTerms.current && JSON.stringify(terms) !== JSON.stringify(retryTerms.current)) terms.request_id = crypto.randomUUID();
    retryTerms.current = terms;
    return employeeAccessApi.prepare(business, terms, token);
  }, retry: false, onSuccess: async () => { clear(); await query.refetch(); }, onError: () => setMfa("") });
  const pending = mutation.isPending || query.isFetching;
  useEffect(() => { onDraft({ dirty, pending }); }, [dirty, pending, onDraft]);
  useEffect(() => () => onDraft({ dirty: false, pending: false }), [onDraft]);
  useEffect(() => setSearchDraft(search), [search]);
  async function discard() {
    if (dirty && !(await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) return false;
    clear(); mutation.reset(); return true;
  }
  async function move(values: Record<string, string>) { if (!pending && await discard()) update(values); }
  async function select(value: AccessTarget) { if (!pending && await discard()) setTarget(value); }
  async function refresh() { if (!mutation.isPending && await discard()) await query.refetch(); }
  async function act(item: AccessRepair, type: "execute" | "cancel") {
    const label = t(`employeeAccess.${type}`);
    if (!(await confirm({ title: label, description: `${item.target_email} · ${t(`employeeAccess.action.${item.action}`)}. ${t("employeeAccess.effects")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ type, item });
  }
  const error = mutation.error ? normalizeAppError(mutation.error) : null;
  if (query.isPending) return <LoadingState />;
  if (!query.data || (query.isError && !retainSupportData(query.error)) || error?.category === "permission") return <PlatformLoadError error={query.error || mutation.error} message={t("platform.merchantDetail.error")} onRetry={() => void refresh()} />;
  const data = query.data;
  const choices: AccessAction[] = !target || target.row.protected ? [] : target.kind === "member"
    ? [...(target.row.membership_active ? ["disable" as const] : target.row.account_active ? ["restore" as const] : []), ...(target.row.account_active ? ["role" as const] : [])]
    : target.row.status === "accepted" ? [] : ["reissue", ...(target.row.status !== "revoked" ? ["revoke" as const] : [])];
  const valid = Boolean(target && choices.includes(action as AccessAction) && caseId && reason.trim() && mfa.trim() && (action !== "role" || role));
  const rows: AccessTarget[] = kind === "member" ? data.members.map(row => ({ kind: "member", row })) : data.invitations.map(row => ({ kind: "invitation", row }));
  const count = kind === "member" ? data.members_count : data.invitations_count;
  return <div className="space-y-4" data-testid="business-employee-access">
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("employeeAccess.title")}</h2><Button variant="secondary" disabled={pending} onClick={() => void refresh()}>{t("common.refresh")}</Button></div>
    {query.isError && <ErrorState error={query.error} action={<Button disabled={pending} onClick={() => query.refetch()}>{t("common.retry")}</Button>} />}
    <div className="grid gap-3 sm:grid-cols-[12rem_1fr]">
      <Select label={t("employeeAccess.records")} disabled={pending} value={kind} options={[{ value: "member", label: t("employeeAccess.members") }, { value: "invitation", label: t("employeeAccess.invitations") }]} onChange={event => void move({ access_kind: event.target.value, access_page: "" })} />
      <form className="flex items-end gap-2" onSubmit={event => { event.preventDefault(); void move({ access_search: searchDraft, access_page: "" }); }}>
        <Input label={t("common.search")} value={searchDraft} maxLength={200} disabled={pending} onChange={event => setSearchDraft(event.target.value)} className="w-full" />
        <Button type="submit" disabled={pending}>{t("common.search")}</Button>
      </form>
    </div>
    <Card>
      {!rows.length && <p className="p-4 text-sm" role="status">{t("employeeAccess.empty")}</p>}
      <ul className="divide-y divide-platforma-border">{rows.map(value => <li key={value.row.id}>
        <button type="button" disabled={pending} aria-pressed={target?.kind === value.kind && target.row.id === value.row.id} className="platforma-focus-ring w-full space-y-1 p-3 text-left hover:bg-surface-hover" onClick={() => void select(value)}>
          <span className="block break-words font-medium">{value.row.name}</span><span className="block break-all text-sm text-platforma-subtle">{value.row.email}</span>
          <span className="block text-sm">{value.kind === "member" ? `${t("employeeAccess.membership")}: ${t(value.row.membership_active ? "employeeAccess.active" : "employeeAccess.inactive")}` : t(`employeeAccess.invitation.${value.row.status}`)}</span>
        </button>
      </li>)}</ul>
      <ClinicPager page={page} count={count} change={next => void move({ access_page: String(next) })} />
    </Card>
    <Card padding="md"><form className="space-y-4" data-testid="access-prepare" onSubmit={event => { event.preventDefault(); if (valid && !pending && !query.isError) mutation.mutate({ type: "prepare" }); }}>
      {target && <EmployeeAccessDiagnostics target={target} />}
      {target && choices.length > 0 && <fieldset disabled={pending || query.isError} className="grid gap-4 sm:grid-cols-2">
        <Select label={t("employeeAccess.action")} value={action} required options={[{ value: "", label: t("common.select") }, ...choices.map(value => ({ value, label: t(`employeeAccess.action.${value}`) }))]} onChange={event => { setAction(event.target.value as AccessAction); setRole(""); }} />
        {action === "role" && <Select label={t("employeeAccess.newRole")} value={role} required options={[{ value: "", label: t("common.select") }, ...data.roles.filter(row => target.kind !== "member" || row.id !== target.row.business_role?.id).map(row => ({ value: row.id, label: row.name }))]} onChange={event => setRole(event.target.value)} />}
        <div className="space-y-2"><Input name="support_case_id" label={t("businessDetails.caseId")} required inputMode="numeric" pattern="[1-9][0-9]*" value={caseId} onChange={event => setCaseId(event.target.value)} /><Button type="button" variant="secondary" onClick={() => setCreatingCase(true)}>{t("supportCases.create")}</Button></div>
        <Textarea label={t("supportCases.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} />
        {action && <p className="text-sm sm:col-span-2" role="status">{t("employeeAccess.effects")} {["restore", "role", "reissue"].includes(action) && t("recovery.waitingOwner")}</p>}
      </fieldset>}
      <Input name="mfa" label={t("mfa.codeLabel")} autoComplete="one-time-code" disabled={pending || query.isError} value={mfa} onChange={event => setMfa(event.target.value)} />
      <div className="flex flex-wrap gap-2">
        {target && choices.length > 0 && <Button type="submit" disabled={!valid || pending || query.isError || error?.category === "conflict"} isLoading={mutation.isPending}>{t("employeeAccess.prepare")}</Button>}
        {dirty && <Button type="button" variant="secondary" disabled={pending} onClick={() => void discard()}>{t("employeeAccess.clear")}</Button>}
      </div>
    </form></Card>
    {error && (["mfa_code_invalid", "mfa_step_up_required"].includes(error.code) ? <p role="alert" className="text-platforma-danger">{t("businessDetails.mfaError")}</p> : <ErrorState error={mutation.error} />)}
    {error?.category === "conflict" && <p role="alert">{t("employeeAccess.conflict")}</p>}
    <h3 className="font-semibold">{t("employeeAccess.requests")}</h3>
    {!data.requests.length && <p role="status" className="text-sm text-platforma-subtle">{t("employeeAccess.noRequests")}</p>}
    {data.requests.map(item => <EmployeeAccessSummary key={item.id} item={item}>
      <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm text-brand-700" to={`/platform/support/${item.support_case_id}`}>{t("businessDetails.caseId")} #{item.support_case_id}</Link>
      {item.status === "pending" && <div className="flex flex-wrap gap-2">
        <Button disabled={pending || query.isError || hasTerms || !mfa.trim() || (item.owner_required && !item.owner_confirmed_at) || error?.category === "conflict"} onClick={() => void act(item, "execute")}>{t("employeeAccess.execute")}</Button>
        <Button variant="secondary" disabled={pending || query.isError || hasTerms || !mfa.trim()} onClick={() => void act(item, "cancel")}>{t("employeeAccess.cancel")}</Button>
      </div>}
    </EmployeeAccessSummary>)}
    {creatingCase && target && <SupportCreateDialog scope={{ platform: true }} initialBusiness={Number(business)} fixedBusiness requester={target.kind === "member" && target.row.account_active && target.row.membership_active ? { id: target.row.user_id, name: target.row.name } : undefined} onClose={() => setCreatingCase(false)} onCreated={item => { setCaseId(String(item.id)); setCreatingCase(false); }} />}
  </div>;
}
