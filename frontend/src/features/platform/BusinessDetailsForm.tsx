import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { platformApi, type BusinessDetails, type BusinessDetailsSnapshot } from "../../api/platform";
import { issueMfaStepUp } from "../../api/auth";
import { normalizeAppError } from "../../api/appError";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Textarea } from "../../components/ui/Textarea";
import { Card, CardBody } from "../../components/ui/Card";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../lib/i18n";
import { PlatformLoadError } from "./PlatformData";

type DraftStatus = { dirty: boolean; pending: boolean };
type Props = { business: string; onDraft: (state: DraftStatus) => void };
export const businessDetailsFields: { key: keyof BusinessDetails; label: string; max: number; type?: string }[] = [
  { key: "name", label: "businessForm.name", max: 255 },
  { key: "legal_name", label: "businessForm.legalName", max: 255 },
  { key: "tax_id", label: "settings.workflow.optionalTaxId", max: 64 },
  { key: "city", label: "businessForm.city", max: 128 },
  { key: "address", label: "businessForm.address", max: 255 },
  { key: "phone", label: "businessForm.phone", max: 32, type: "tel" },
  { key: "whatsapp", label: "WhatsApp", max: 64 },
  { key: "telegram", label: "Telegram", max: 64 },
  { key: "instagram", label: "Instagram", max: 64 },
  { key: "invoice_email", label: "businessForm.invoiceEmail", max: 254, type: "email" },
];
const fields = businessDetailsFields;

export function BusinessDetailsForm(props: Props) {
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["platform-business-details", props.business], queryFn: () => platformApi.details(props.business), gcTime: 0, retry: false, refetchOnWindowFocus: false });
  if (query.isPending) return <LoadingState />;
  if (!query.data || query.isError) return <PlatformLoadError error={query.error} message={t("platform.merchantDetail.error")} onRetry={() => query.refetch()} />;
  return <DetailsEditor {...props} initial={query.data} />;
}

function DetailsEditor({ business, initial, onDraft }: Props & { initial: BusinessDetailsSnapshot }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const [snapshot, setSnapshot] = useState(initial);
  const [draft, setDraft] = useState(initial.details);
  const [caseId, setCaseId] = useState("");
  const [reason, setReason] = useState("");
  const [mfa, setMfa] = useState("");
  const [reloadError, setReloadError] = useState<unknown>(null);
  const [reloading, setReloading] = useState(false);
  const changes = Object.fromEntries(fields.filter(({ key }) => draft[key] !== snapshot.details[key]).map(({ key }) => [key, draft[key]]));
  const dirty = Object.keys(changes).length > 0 || !!reason || !!caseId;
  const save = useMutation({
    mutationFn: async () => {
      const token = await issueMfaStepUp(mfa);
      return platformApi.correctDetails(business, { changes, expected_revision: snapshot.revision, support_case_id: Number(caseId), reason }, token.step_up_token);
    },
    retry: false,
    onSuccess: result => {
      setSnapshot(result); setDraft(result.details); setReason(""); setCaseId(""); setMfa("");
      queryClient.setQueryData(["platform-business-details", business], result);
      for (const key of ["platform-merchant", "platform-merchants", "platform-overview", "platform-clinic-access"]) void queryClient.invalidateQueries({ queryKey: [key] });
    },
    onError: () => setMfa(""),
  });
  const pending = save.isPending || reloading;
  useEffect(() => { onDraft({ dirty, pending }); }, [dirty, pending, onDraft]);
  useEffect(() => () => onDraft({ dirty: false, pending: false }), [onDraft]);
  async function reload() {
    if (dirty && !(await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" })).confirmed) return;
    setReloading(true); setReloadError(null);
    try {
      const result = await platformApi.details(business);
      setSnapshot(result); setDraft(result.details); setReason(""); setCaseId(""); setMfa(""); save.reset();
      queryClient.setQueryData(["platform-business-details", business], result);
    } catch (error) { setReloadError(error); }
    finally { setReloading(false); }
  }
  const error = save.error ? normalizeAppError(save.error) : null;
  const mfaError = error && ["mfa_code_invalid", "mfa_step_up_required"].includes(error.code);
  const denied = error?.category === "permission" || (!!reloadError && normalizeAppError(reloadError).category === "permission");
  if (denied) return <PlatformLoadError error={reloadError || save.error} message={t("platform.merchantDetail.error")} onRetry={() => void reload()} />;
  return <Card><CardBody><form data-testid="business-details-form" className="space-y-5" onSubmit={event => { event.preventDefault(); if (!pending && Object.keys(changes).length && error?.category !== "conflict") save.mutate(); }}>
    <fieldset disabled={pending || !snapshot.actions.update} className="grid gap-4 sm:grid-cols-2">
      {fields.map(field => <Input key={field.key} name={field.key} label={field.label.includes(".") ? t(field.label) : field.label} value={draft[field.key]} type={field.type || "text"} maxLength={field.max} required={field.key === "name"} onChange={event => { setDraft(current => ({ ...current, [field.key]: event.target.value })); if (save.isSuccess) save.reset(); }} />)}
      <Input name="support_case_id" label={t("businessDetails.caseId")} inputMode="numeric" pattern="[1-9][0-9]*" required value={caseId} onChange={event => setCaseId(event.target.value)} />
      <Input name="mfa" label={t("mfa.codeLabel")} autoComplete="one-time-code" required value={mfa} onChange={event => setMfa(event.target.value)} />
      <div className="sm:col-span-2"><Textarea label={t("supportCases.reason")} required maxLength={2000} value={reason} onChange={event => setReason(event.target.value)} /></div>
    </fieldset>
    {mfaError ? <p role="alert" className="text-sm text-platforma-danger">{t("businessDetails.mfaError")}</p> : save.isError && <ErrorState error={save.error} />}
    {error?.category === "conflict" && <p role="status" className="text-sm text-platforma-warning">{t("businessDetails.conflict")}</p>}
    {reloadError ? <ErrorState error={reloadError} /> : null}
    {save.isSuccess && <p role="status" className="text-sm text-platforma-success">{t("common.saved")}</p>}
    <div className="flex flex-wrap gap-3"><Button type="submit" isLoading={save.isPending} disabled={pending || !snapshot.actions.update || !Object.keys(changes).length || !reason.trim() || !mfa.trim() || !caseId || error?.category === "conflict"}>{t("common.save")}</Button><Button type="button" variant="secondary" disabled={pending} onClick={() => void reload()}>{t("common.refresh")}</Button></div>
  </form></CardBody></Card>;
}
