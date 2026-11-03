import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { appointmentsApi } from "../../api/appointments";
import { leadsApi } from "../../api/leads";
import { dealsApi } from "../../api/deals";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { RecordsTable } from "./RecordsTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { formatDateTime } from "../../lib/format";
import { formatTimelineEventText } from "../../components/crm/drawers/timelineHelpers";
import { EntityAttachmentsPanel } from "../../components/crm/drawers/EntityAttachmentsPanel";
import { LeadCaptureFormsModal } from "../leads/components/LeadCaptureFormsModal";
import { ImportPanel } from "../integrations/components/ImportPanel";
import { Modal } from "../../components/ui/Modal";
import { hasPermission } from "../../lib/permissions";
import { LegacyAssignment } from "./LegacyAssignment";
import { EntityCustomFieldsPanel } from "../../components/crm/drawers/EntityCustomFieldsPanel";
import { importExportApi } from "../../api/importExport";
import { ExportHistory } from "../analytics/ExportHistory";

export function LegacyRecordsPage({ kind }: { kind: "lead" | "deal" }) {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t, language } = useI18n();
  const rawId = id || params.get(kind);
  const objectId = Number(rawId);
  const validId = Number.isSafeInteger(objectId) && objectId > 0;
  const page = Math.max(1, Number(params.get("page")) || 1);
  const query = useQuery({
    queryKey: ["legacy-record-links", user?.id, business?.id, kind, objectId, page],
    queryFn: () => appointmentsApi.legacyLinks({ business: business!.id, kind, object_id: objectId, page }),
    enabled: !!business && validId,
  });
  if (!rawId) return <LegacyHistoryList kind={kind} />;
  if (!validId || !business) return <EmptyState title={t("records.legacyUnavailable")} />;
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  const changePage = (value: number) => setParams(current => { const next = new URLSearchParams(current); next.set("page", String(value)); return next; });
  const card = query.data.source.card;
  const source = kind === "lead" ? card.lead : card.deal;
  return <div className="space-y-4">
    <h1 className="text-xl font-semibold">{t("records.legacyTitle")}</h1>
    <div className="flex flex-wrap gap-4">
      <Link className="platforma-focus-ring text-brand-700" to="/app/appointments">{t("appointments.title")}</Link>
      {query.data.source.client ? <Link className="platforma-focus-ring text-brand-700" to={`/app/clients/${query.data.source.client}`}>{t("nav.clients")}</Link> : null}
    </div>
    {source ? <section className="space-y-3 rounded-card border border-platforma-border p-4">
      <h2 className="font-semibold">{t(kind === "lead" ? "crmCard.leadNumber" : "conversations.dealFallback", { id: source.id })}</h2>
      <StatusBadge status={source.status} />
      {kind === "lead" && card.lead?.message ? <p className="whitespace-pre-wrap break-words">{card.lead.message}</p> : null}
      {kind === "deal" && card.deal?.title ? <p className="break-words">{card.deal.title}</p> : null}
      {source.lost_reason ? <p className="whitespace-pre-wrap break-words">{source.lost_reason}</p> : null}
      {kind === "deal" && card.deal?.notes ? <p className="whitespace-pre-wrap break-words">{card.deal.notes}</p> : null}
      <LegacyAssignment key={`${kind}:${source.id}`} source={source} kind={kind} />
    </section> : null}
    {query.data.results.length ? <RecordsTable records={query.data.results} timeZone={business.timezone || "Asia/Qyzylorda"} /> : <EmptyState title={t("records.legacyEmpty")} />}
    <div className="flex gap-2">
      <Button disabled={!query.data.previous} onClick={() => changePage(page - 1)}>{t("pagination.previous")}</Button>
      <Button disabled={!query.data.next} onClick={() => changePage(page + 1)}>{t("pagination.next")}</Button>
    </div>
    <section className="space-y-3" aria-label={t("tasks.history")}>
      <h2 className="font-semibold">{t("tasks.history")}</h2>
      {card.timeline.map(event => <div key={event.id} className="rounded-control border border-platforma-border p-3">
        <p className="whitespace-pre-wrap break-words">{formatTimelineEventText(event, t)}</p>
        <p className="text-sm text-platforma-muted">{formatDateTime(event.created_at, business.timezone, true, language)}</p>
      </div>)}
      {card.meta?.has_more.timeline ? <Link className="platforma-focus-ring text-brand-700" to={`/app/timeline?entity_type=${kind === "lead" ? "Lead" : "Deal"}&entity_id=${objectId}`}>{t("nav.timeline")}</Link> : null}
    </section>
    <EntityAttachmentsPanel data={card} entity={{ type: kind, id: objectId }} readOnly />
    {card.notes.length ? <section aria-label={t("crmCard.notes")} className="space-y-2">
      <h2 className="font-semibold">{t("crmCard.notes")}</h2>
      {card.notes.map(note => <p key={note.id} className="whitespace-pre-wrap break-words rounded-control border border-platforma-border p-3">{note.text}</p>)}
    </section> : null}
    <EntityCustomFieldsPanel data={{ ...card, custom_fields: card.custom_fields.map(field => ({ ...field, can_edit: false })) }} entity={{ type: kind, id: objectId }} />
  </div>;
}

function LegacyHistoryList({ kind }: { kind: "lead" | "deal" }) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const [formsOpen, setFormsOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [exportsOpen, setExportsOpen] = useState(false);
  const exportRows = useMutation({
    mutationFn: () => importExportApi.exportEntity({ business: business!.id, entity: kind === "lead" ? "leads" : "deals" }),
    onSuccess: job => { if (job) setExportsOpen(true); },
  });
  const page = Math.max(1, Number(params.get("page")) || 1);
  const responsible = Number(params.get("responsible_user")) || undefined;
  const owner = Number(params.get("owner")) || undefined;
  const query = useQuery({
    queryKey: ["legacy-history", business?.id, user?.id, kind, page, responsible, owner],
    queryFn: async () => {
      const response = kind === "lead"
        ? await leadsApi.listPaginated({ business: business!.id, page, responsible_user: responsible })
        : await dealsApi.listPaginated({ business: business!.id, page, owner });
      return { ...response, results: response.results.map(item => ({ id: item.id, status: item.status, title: "title" in item ? item.title : item.client_name })) };
    }, enabled: !!business,
  });
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  const change = (value: number) => setParams(current => { const next = new URLSearchParams(current); next.set("page", String(value)); return next; });
  return <div className="space-y-4">
    <h1 className="text-xl font-semibold">{t("records.legacyTitle")}</h1>
    <div className="flex flex-wrap gap-2">
      <Link className="platforma-focus-ring text-brand-700" to="/app/appointments">{t("appointments.title")}</Link>
      {kind === "lead" ? <Button variant="secondary" onClick={() => setFormsOpen(true)}>{t("settings.leadFormsTitle")}</Button> : null}
      <Button variant="secondary" isLoading={exportRows.isPending} onClick={() => exportRows.mutate()}>{t("leads.exportCsv")}</Button>
      <Button variant="secondary" onClick={() => setExportsOpen(true)}>{t("exportHistory.title")}</Button>
      {hasPermission(user, business?.id, kind === "lead" ? "leads" : "deals", "create") ? <Button variant="secondary" onClick={() => setImportOpen(true)}>{t("leads.import")}</Button> : null}
    </div>
    {exportRows.error ? <ErrorState error={exportRows.error} /> : null}
    {query.data.results.map(item => <div key={item.id} className="flex items-center justify-between gap-3 rounded-card border border-platforma-border p-3">
      <Link className="platforma-focus-ring text-brand-700" to={`/app/${kind === "lead" ? "leads" : "deals"}/${item.id}`}>{item.title || `#${item.id}`}</Link>
      <StatusBadge status={item.status} />
    </div>)}
    {!query.data.results.length ? <EmptyState title={t("records.legacyEmpty")} /> : null}
    <div className="flex gap-2"><Button disabled={!query.data.previous} onClick={() => change(page-1)}>{t("pagination.previous")}</Button><Button disabled={!query.data.next} onClick={() => change(page+1)}>{t("pagination.next")}</Button></div>
    {formsOpen && business ? <LeadCaptureFormsModal business={business.id} onClose={() => setFormsOpen(false)} /> : null}
    <Modal open={exportsOpen} onClose={() => setExportsOpen(false)} title={t("exportHistory.title")} size="xl">
      {business && user ? <ExportHistory business={business} userId={user.id} /> : null}
    </Modal>
    <Modal open={importOpen} onClose={() => setImportOpen(false)} title={t("leads.import")} size="xl">
      {business ? <ImportPanel businessId={business.id} allowedEntities={[kind === "lead" ? "leads" : "deals"]} initialEntity={kind === "lead" ? "leads" : "deals"} /> : null}
    </Modal>
  </div>;
}
