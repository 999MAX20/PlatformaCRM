import { useId, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Pencil, Plus, Trash2 } from "lucide-react";
import type { ClinicalContent, ClinicalProcedureItem } from "../../api/medicalClinical";
import { servicesApi } from "../../api/services";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Textarea } from "../../components/ui/Textarea";
import { Modal } from "../../components/ui/Modal";
import { ActionMenu } from "../../components/ui/ActionMenu";
import { ClinicalPlanTeeth } from "./ClinicalPlanTeeth";
import { useI18n } from "../../lib/i18n";

export function AppointmentTreatmentTable({ content, onChange, disabled, readOnly, onEditing, onLegacy }: {
  content: ClinicalContent; onChange: (value: ClinicalContent) => void; disabled: boolean; readOnly: boolean;
  onEditing: (value: boolean) => void; onLegacy: () => void;
}) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<ClinicalProcedureItem | "new" | null>(null);
  const items = content.procedure_items ?? [];
  function close() { setEditing(null); onEditing(false); }
  function open(item: ClinicalProcedureItem | "new") { setEditing(item); onEditing(true); }
  return <section className="appointment-summary-card">
    <div className="appointment-section-heading"><h2>{t("medical.page.treatment")}</h2>
      <div className="flex items-center gap-2">{!readOnly && <Button variant="ghost" disabled={disabled || items.length >= 100} onClick={() => open("new")}><Plus size={18} />{t("medical.page.addTreatment")}</Button>}
        <ActionMenu label={t("medical.clinical.procedures")} items={[{ key: "description", label: t("medical.clinical.procedures"), icon: Pencil, onSelect: onLegacy, disabled }]} />
      </div>
    </div>
    <div className="appointment-treatment-scroll"><table className="appointment-treatment-table">
      <thead><tr><th>{t("appointment.service")}</th><th>{t("medical.tooth.tooth")}</th><th>{t("medical.page.description")}</th><th>{t("medical.page.duration")}</th><th>{t("medical.page.status")}</th><th><span className="sr-only">{t("appointments.actions")}</span></th></tr></thead>
      <tbody>{items.map(item => <tr key={item.id}>
        <td>{item.service_name}</td><td>{item.teeth.join(", ") || "—"}</td><td>{item.description || "—"}</td>
        <td>{t("medical.page.minutes", { count: item.duration_minutes })}</td><td><span className="appointment-treatment-done"><Check size={14} />{t("medical.page.done")}</span></td>
        <td>{!readOnly && <Button variant="ghost" size="icon" disabled={disabled} aria-label={t("medical.page.editTreatment", { name: item.service_name })} onClick={() => open(item)}><Pencil size={16} /></Button>}</td>
      </tr>)}{!items.length && <tr><td colSpan={6}>{content.not_applicable?.procedures || t("medical.clinical.notRecorded")}</td></tr>}</tbody>
    </table></div>
    {!!content.procedures && <button className="appointment-field-preview text-left" disabled={disabled} onClick={onLegacy}>{content.procedures}</button>}
    {editing && <TreatmentEditor key={editing === "new" ? "new" : editing.id} item={editing === "new" ? undefined : editing}
      onClose={close} onApply={item => {
        const notApplicable = { ...content.not_applicable }; delete notApplicable.procedures;
        onChange({ ...content, not_applicable: notApplicable, procedure_items: editing === "new" ? [...items, item] : items.map(existing => existing.id === item.id ? item : existing) }); close();
      }} onRemove={editing === "new" ? undefined : () => { onChange({ ...content, procedure_items: items.filter(item => item.id !== editing.id) }); close(); }} />}
  </section>;
}

function TreatmentEditor({ item, onClose, onApply, onRemove }: {
  item?: ClinicalProcedureItem; onClose: () => void; onApply: (item: ClinicalProcedureItem) => void; onRemove?: () => void;
}) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const listId = useId();
  const formId = useId();
  const [initial] = useState<ClinicalProcedureItem>(() => item ?? { id: crypto.randomUUID(), service_name: "", teeth: [], description: "", duration_minutes: 0 });
  const [draft, setDraft] = useState(initial);
  const catalog = useQuery({ queryKey: ["services", "treatment", business?.id, user?.id],
    queryFn: () => servicesApi.listAll({ business: business!.id, status: "active" }), enabled: !!business?.id });
  const close = () => { if (JSON.stringify(draft) === JSON.stringify(initial) || window.confirm(t("medical.clinical.discard"))) onClose(); };
  return <Modal open title={t(item ? "medical.page.editTreatmentTitle" : "medical.page.addTreatment")} onClose={close} closeOnBackdrop={false} size="md" className="appointment-field-modal"
    footer={<><Button variant="secondary" onClick={close}>{t("common.cancel")}</Button><Button type="submit" form={formId}>{t("medical.page.apply")}</Button></>}>
    <form id={formId} className="space-y-4" onSubmit={event => { event.preventDefault(); if (draft.service_name.trim()) onApply({ ...draft, service_name: draft.service_name.trim() }); }}>
      <Input label={t("appointment.service")} required maxLength={255} list={listId} value={draft.service_name} onChange={event => {
        const service = catalog.data?.find(value => value.name === event.target.value);
        setDraft({ ...draft, service_name: event.target.value, duration_minutes: service?.duration_minutes || draft.duration_minutes });
      }} />
      <datalist id={listId}>{catalog.data?.map(service => <option key={service.id} value={service.name} />)}</datalist>
      {catalog.isError && <p role="status" className="text-sm">{t("medical.page.catalogUnavailable")} <Button variant="ghost" onClick={() => void catalog.refetch()}>{t("common.retry")}</Button></p>}
      <ClinicalPlanTeeth value={draft.teeth} disabled={false} readOnly={false} onChange={teeth => setDraft({ ...draft, teeth })} />
      <Textarea label={t("medical.page.description")} value={draft.description} maxLength={4000} rows={3} onChange={event => setDraft({ ...draft, description: event.target.value })} />
      <Input label={t("medical.page.durationMinutes")} type="number" min={1} max={1440} required value={draft.duration_minutes || ""} onChange={event => setDraft({ ...draft, duration_minutes: Number(event.target.value) })} />
      <p className="appointment-treatment-done"><Check size={16} />{t("medical.page.done")}</p>
      {onRemove && <Button type="button" variant="ghost" onClick={() => { if (window.confirm(t("medical.page.removeTreatmentConfirm"))) onRemove(); }}><Trash2 size={16} />{t("medical.page.removeTreatment")}</Button>}
    </form>
  </Modal>;
}
