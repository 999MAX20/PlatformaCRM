import { useEffect, useState } from "react";
import type { PlanStepInput } from "../../api/visitPlans";
import { ClientPicker } from "../../components/forms/ClientPicker";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { Resource, Service } from "../../types";

type DraftStep = PlanStepInput & { key: string };
export function PlanEditor({ businessId, clientId, services, resources, branches, members, initial, revision, onSave, pending }: {
  businessId: number; clientId?: number; services: Service[]; resources: Resource[];
  branches: { id: number; name: string }[]; members: { id: number; name: string }[];
  initial?: PlanStepInput; revision?: number; pending: boolean;
  onSave: (values: { client: number; responsible_user?: number; steps: PlanStepInput[]; reason: string; consent: boolean }) => Promise<unknown>;
}) {
  const { t } = useI18n();
  const [client, setClient] = useState(clientId || 0);
  const [responsible, setResponsible] = useState(members[0]?.id);
  const [steps, setSteps] = useState<DraftStep[]>([{ ...(initial || { service: 0 }), key: crypto.randomUUID() }]);
  const [reason, setReason] = useState("");
  const [consent, setConsent] = useState(false);
  useEffect(() => setConsent(false), [revision]);
  const change = (index: number, field: keyof PlanStepInput, value: string | number) => setSteps(current => current.map((step, i) => i === index ? { ...step, [field]: Number(value) || null } : step));
  return <form className="space-y-4" onSubmit={event => {
    event.preventDefault();
    void onSave({ client, responsible_user: responsible, steps: steps.map(({ key: _key, ...step }) => step), reason, consent });
  }}>
    {!revision ? <>
      <ClientPicker businessId={businessId} value={String(client || "")} onChange={value => setClient(Number(value))} />
      <Select label={t("appointment.responsible")} value={responsible || ""} options={members.map(member => ({ value: member.id, label: member.name }))} onChange={event => setResponsible(Number(event.target.value))} />
    </> : null}
    {steps.map((step, index) => <fieldset key={step.key} className="space-y-3 rounded-card border border-platforma-border p-4">
      <legend className="px-1 text-sm font-semibold">{t("plans.step")} {index + 1}</legend>
      <Select label={t("appointment.service")} value={step.service || ""} required options={[{ value: "", label: t("appointment.selectService") }, ...services.filter(service => service.is_active && !service.is_archived).map(service => ({ value: service.id, label: service.name }))]} onChange={event => change(index, "service", event.target.value)} />
      <Select label={t("appointment.resource")} value={step.resource || ""} options={[{ value: "", label: t("plans.notAssigned") }, ...resources.filter(resource => resource.is_active && !resource.retired_at && resource.resource_type === "staff").map(resource => ({ value: resource.id, label: resource.name }))]} onChange={event => change(index, "resource", event.target.value)} />
      {branches.length ? <Select label={t("records.branch")} value={step.branch || ""} options={[{ value: "", label: t("plans.notAssigned") }, ...branches.map(branch => ({ value: branch.id, label: branch.name }))]} onChange={event => change(index, "branch", event.target.value)} /> : null}
      <Select label={t("appointment.responsible")} value={step.responsible_user || ""} options={[{ value: "", label: t("plans.inheritResponsible") }, ...members.map(member => ({ value: member.id, label: member.name }))]} onChange={event => change(index, "responsible_user", event.target.value)} />
      {!initial && steps.length > 1 ? <Button type="button" variant="secondary" onClick={() => setSteps(current => current.filter((_, i) => i !== index))}>{t("plans.remove")}</Button> : null}
    </fieldset>)}
    {!initial ? <Button type="button" variant="secondary" disabled={steps.length >= 100} onClick={() => setSteps(current => [...current, { service: 0, key: crypto.randomUUID() }])}>{t("plans.addStep")}</Button> : null}
    {revision ? <>
      <Textarea label={t("plans.reason")} value={reason} onChange={event => setReason(event.target.value)} required maxLength={500} />
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} required />{t("plans.consent")}</label>
    </> : null}
    <div><Button type="submit" isLoading={pending} disabled={!client || steps.some(step => !step.service) || (!!revision && (!reason.trim() || !consent))}>{t("common.save")}</Button></div>
  </form>;
}
