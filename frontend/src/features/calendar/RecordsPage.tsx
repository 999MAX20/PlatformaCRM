import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { normalizeAppError } from "../../api/appError";
import { appointmentsApi, type AppointmentCreatePayload } from "../../api/appointments";
import { branchesApi } from "../../api/branches";
import { clientsApi } from "../../api/clients";
import { teamApi } from "../../api/team";
import { useActionFeedback } from "../../components/actions/useActionFeedback";
import { CrmPagination } from "../../components/crm/CrmPagination";
import { AppointmentForm } from "../../components/forms/AppointmentForm";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import { todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { RecordsToolbar } from "./RecordsToolbar";
import { RecordsTableView } from "./RecordsTable";
import { useCustomColumns } from "../../components/crm/CustomFieldColumns";
import { RecordsLoadError } from "./RecordsLoadError";
import { recordWorkspaceParams, resetRecordFilters } from "./recordFilters";
import { useCalendarCatalog } from "./useCalendarCatalog";
import { VisitPlansPage } from "./VisitPlansPage";
import { useRecordsPeriod } from "./useRecordsPeriod";
import { RecordsEmptyState } from "./RecordsEmptyState";

export function RecordsPage() {
  const [params] = useSearchParams();
  return params.get("view") === "plans" ? <VisitPlansPage /> : <RecordsListPage />;
}

function RecordsListPage() {
  const [periodOpen, setPeriodOpen] = useState(false);
  const { t } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const navigate = useNavigate();
  const { params, setParams, periodReady } = useRecordsPeriod(business?.id, user?.id);
  const { setPageHeader } = usePageHeader();
  const { notifyError, notifySuccess } = useActionFeedback();
  const cache = useQueryClient();
  const createView = useRef({ open: false, mounted: true, scope: "" });
  const submissionScope = useRef("");
  const createPending = useRef(false);
  createView.current.scope = `${business?.id}:${user?.id}`;
  createView.current.open = params.get("create") === "1";
  useEffect(() => { createView.current.mounted = true; return () => { createView.current.mounted = false; }; }, []);
  const attempt = useRef<{ payload: string; key: string } | null>(null);
  const timeZone = business?.timezone || "Asia/Qyzylorda";
  const today = todayInTimeZone(timeZone);
  const filters = recordWorkspaceParams(params, today, business?.id || 0);
  const canCreate = hasPermission(user, business?.id, "appointments", "create");
  const sourceClient = Number(params.get("client")) || undefined;
  const sourceClientQuery = useQuery({
    queryKey: ["clients", "record-source", business?.id, user?.id, sourceClient],
    queryFn: () => clientsApi.get(sourceClient!),
    enabled: params.get("create") === "1" && !!params.get("conversation") && !!sourceClient && canCreate && hasPermission(user, business?.id, "clients", "view"),
    retry: false,
  });
  const catalog = useCalendarCatalog(business?.id, user?.id, false, false);
  const branches = useQuery({ queryKey: ["branches", business?.id, user?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  const members = useQuery({ queryKey: ["team-members", "appointment", business?.id, user?.id], queryFn: () => teamApi.allMembers(business!.id), enabled: !!business && hasPermission(user, business.id, "team", "view") });
  const records = useQuery({ queryKey: ["appointments", "workspace", user?.id, filters], queryFn: () => appointmentsApi.workspace(filters), enabled: !!business && periodReady, refetchInterval: 30000,
    placeholderData: (previous, previousQuery) => previousQuery?.queryKey[2] === user?.id &&
      (previousQuery?.queryKey[3] as { business?: number } | undefined)?.business === business?.id ? previous : undefined });
  const showHeaderCreate = canCreate && !(records.isSuccess && !records.isPlaceholderData && records.data.results.length === 0);
  const filtered = [filters.q, filters.workflow, filters.attention, filters.client, filters.resource, filters.physical_resource, filters.responsible_user, filters.confirmed, filters.branch, filters.custom_field].some(Boolean);
  const availability = useQuery({
    queryKey: ["appointments", "availability", business?.id, user?.id],
    queryFn: () => appointmentsApi.workspace({ business: business!.id, page_size: 1 }),
    enabled: !!business && !filtered && records.isSuccess && !records.isPlaceholderData && records.data.results.length === 0,
  });
  const isEmptyWorkspace = !filtered && records.isSuccess && !records.isPlaceholderData && records.data.results.length === 0 && availability.isSuccess && availability.data.count === 0;
  const customTable = useCustomColumns(business?.id || 0, "appointment", (records.data?.results || []).map(record => record.id));
  usePageLoading(!periodReady || records.isLoading);
  const update = (key: string, value: string) => setParams(current => {
    const next = new URLSearchParams(current);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page" && key !== "create") next.delete("page");
    return next;
  });
  const closeCreate = () => setParams(current => {
    const next = new URLSearchParams(current);
    ["create", "conversation"].forEach(key => next.delete(key));
    return next;
  });
  useEffect(() => {
    setPageHeader({ title: t("appointments.title"), primaryAction: showHeaderCreate ? { label: t("appointments.create"), icon: Plus, onClick: () => setParams(current => { const next = new URLSearchParams(current); next.set("create", "1"); return next; }) } : undefined });
    return () => setPageHeader(null);
  }, [setPageHeader, setParams, t, showHeaderCreate]);
  const create = useMutation({
    mutationFn: (payload: AppointmentCreatePayload) => {
      createPending.current = true;
      submissionScope.current = createView.current.scope;
      const fingerprint = JSON.stringify(payload);
      if (attempt.current?.payload !== fingerprint) attempt.current = { payload: fingerprint, key: crypto.randomUUID() };
      return appointmentsApi.createRecord(payload, attempt.current.key);
    },
    onSuccess: async record => {
      const stayInCreate = createView.current.mounted && createView.current.open && submissionScope.current === createView.current.scope;
      attempt.current = null;
      if (stayInCreate) closeCreate();
      notifySuccess(t("common.saved"));
      if (stayInCreate && "id" in record) navigate(`/app/appointments/${record.id}`);
      await refreshAppointmentQueries(cache, "id" in record ? record : undefined);
    },
    onError: error => notifyError(error),
    onSettled: () => { createPending.current = false; },
  });
  useEffect(() => {
    if (records.isError && normalizeAppError(records.error).status === 404 && Number(filters.page) > 1) {
      setParams(current => { const next = new URLSearchParams(current); next.delete("page"); return next; }, { replace: true });
    }
  }, [records.isError, records.error, filters.page, setParams]);
  if (!business) return <EmptyState title={t("appointments.noBusiness")} />;
  const catalogError = catalog.services.error || catalog.resources.error || branches.error || members.error;
  return <div className="flex min-h-[calc(100dvh-var(--app-header-height)-8.5rem)] flex-col gap-4 pt-2 sm:min-h-[calc(100dvh-var(--app-header-height)-9rem)] lg:min-h-[calc(100dvh-var(--app-header-height)-2rem)]" data-testid="records-workspace" aria-busy={records.isFetching}>
    <RecordsToolbar calendarOnly={isEmptyWorkspace} params={params} setParams={setParams} today={today} filters={filters} summary={records.data?.summary} periodOpen={periodOpen} setPeriodOpen={setPeriodOpen}
      resources={(catalog.resources.data || []).filter(item => item.resource_type === "staff").map(item => ({ value: item.id, label: item.name }))}
      physicalResources={(catalog.resources.data || []).filter(item => item.resource_type === "room" || item.resource_type === "equipment").map(item => ({ value: item.id, label: item.name }))}
      branches={(branches.data || []).map(item => ({ value: item.id, label: item.name }))}
      members={[{ value: user!.id, label: user!.full_name || user!.email }, ...(members.data || []).filter(item => item.user.id !== user?.id && item.is_active).map(item => ({ value: item.user.id, label: item.user.full_name || item.user.email }))]} />
    {catalogError ? <ErrorState error={catalogError} action={<Button onClick={() => { void catalog.services.refetch(); void catalog.resources.refetch(); void branches.refetch(); if (members.isEnabled) void members.refetch(); }}>{t("common.retry")}</Button>} /> : null}
    {!isEmptyWorkspace && customTable.toolbar}
    {records.isError ? <RecordsLoadError error={records.error} retry={() => void records.refetch()} />
      : records.isPending || (records.isPlaceholderData && !records.data?.results.length) ? <LoadingState />
      : records.data?.results.length ? <>{records.isPlaceholderData && <p role="status" className="text-sm text-platforma-subtle">{t("common.loading")}</p>}
        <RecordsTableView records={records.data.results} customColumns={customTable.columns} timeZone={timeZone} showBranch={(branches.data?.length || 0) > 0} onOpen={id => navigate(`/app/appointments/${id}`, { state: { recordReturnTo: `/app/appointments?${params}` } })} />
        <CrmPagination compact shown={records.data.results.length} total={records.data.count} page={Number(filters.page)} pageSize={Number(filters.page_size)} onPageChange={page => update("page", String(page))} onPageSizeChange={size => update("page_size", String(size))} previousLabel={t("pagination.previous")} nextLabel={t("pagination.next")} />
      </> : <RecordsEmptyState businessId={business.id} userId={user?.id} filtered={filtered} singleDay={!!filters.start_from && (!params.get("to") || params.get("to") === filters.start_from)} canCreate={canCreate}
        onCreate={() => update("create", "1")} onChooseDate={() => setPeriodOpen(true)} onReset={() => setParams(current => resetRecordFilters(current, today))} />}
    <Modal open={params.get("create") === "1" && canCreate} onClose={() => { if (!createPending.current) closeCreate(); }} title={t("appointments.create")}>
      {sourceClientQuery.error ? <ErrorState error={sourceClientQuery.error} action={<Button onClick={() => void sourceClientQuery.refetch()}>{t("common.retry")}</Button>} /> : null}
      {catalog.services.isPending || catalog.resources.isPending ? <LoadingState /> : catalog.services.error || catalog.resources.error ? <ErrorState error={catalog.services.error || catalog.resources.error} /> :
        <AppointmentForm recordFirst businessId={business.id} currency={business.currency} timeZone={timeZone} clients={sourceClientQuery.data?.business === business.id ? [sourceClientQuery.data] : []} services={catalog.services.data || []} resources={catalog.resources.data || []} leads={[]}
          prefill={{ service: Number(params.get("service")) || undefined, resource: Number(params.get("resource")) || undefined, date: filters.start_from, client: Number(params.get("client")) || undefined, source_conversation: Number(params.get("conversation")) || undefined, branch: Number(filters.branch) || undefined }}
          onSubmit={payload => create.mutateAsync(payload)} />}
    </Modal>
  </div>;
}
