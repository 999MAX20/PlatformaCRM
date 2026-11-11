import { useCustomColumns, customFilterParams } from "../../components/crm/CustomFieldColumns";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { getApiErrorMessage } from "../../api/client";
import { resourcesApi } from "../../api/resources";
import { teamApi } from "../../api/team";
import { workingHoursApi } from "../../api/workingHours";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { DraftGuard } from "../../components/actions/DraftGuard";
import { CrmWorkspacePage } from "../../components/crm";
import { ResourceCreateForm } from "./components/ResourceCreateForm";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useNotification } from "../../components/notifications/NotificationProvider";
import { DataTable } from "../../components/tables/DataTable";
import type { DataTableRowInteraction } from "../../components/tables/DataTable";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission, permissionForbiddenMessage } from "../../lib/permissions";
import type { Id, Resource } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { BusinessBranchFilter } from "../business/components/BusinessBranchFilter";
import { StaffAccounts } from "../business/components/StaffAccounts";
import { BusinessWorkspaceNav } from "../business/components/BusinessWorkspaceNav";
import { ResourceActionsMenu } from "./components/ResourceActionsMenu";
import { ResourceEditModal } from "./components/ResourceEditModal";
import { ResourceStatusBadge } from "./components/ResourceStatusBadge";
import { ResourcesToolbar, resourceTypeLabelKeys } from "./components/ResourcesToolbar";

const DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZES = new Set([10, 20, 30, 50, 100]);
const RESOURCE_TYPES = new Set<Resource["resource_type"]>(["staff", "room", "hall", "box", "equipment", "other"]);

function positiveInteger(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function validResourceType(value: string | null): Resource["resource_type"] | "" {
  return value && RESOURCE_TYPES.has(value as Resource["resource_type"])
    ? value as Resource["resource_type"]
    : "";
}

export function ResourcesPage({ mode = "physical" }: { mode?: "staff" | "physical" }) {
  const { t } = useI18n();
  const showNotification = useNotification();
  const confirmAction = useActionConfirm();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { setPageHeader } = usePageHeader();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const canManage = hasPermission(user, business?.id, "settings", "update");
  const [searchParams, setSearchParams] = useSearchParams();
  const customFilters = customFilterParams(searchParams);
  const [createOpen, setCreateOpen] = useState(false);
  const [createDirty, setCreateDirty] = useState(false);
  const savedRef = useRef(false);
  const [accountsOpen, setAccountsOpen] = useState(false);
  const [createDraft, setCreateDraft] = useState<Partial<Resource> | undefined>();
  const [inspectorDirty, setInspectorDirty] = useState(false);
  useEffect(() => { if (inspectorDirty || createDirty) savedRef.current = false; }, [inspectorDirty, createDirty]);

  const search = searchParams.get("search") || "";
  const [searchDraft, setSearchDraft] = useState(search);
  const requestedType = validResourceType(searchParams.get("type"));
  const resourceType = mode === "staff" ? "staff" : requestedType === "staff" ? "" : requestedType;
  const branch = positiveInteger(searchParams.get("branch"), 0) || undefined;
  const statusParam = searchParams.get("status");
  const status = statusParam === "active" || statusParam === "inactive" ? statusParam : "";
  const page = positiveInteger(searchParams.get("page"), 1);
  const requestedPageSize = positiveInteger(searchParams.get("page_size"), DEFAULT_PAGE_SIZE);
  const pageSize = PAGE_SIZES.has(requestedPageSize) ? requestedPageSize : DEFAULT_PAGE_SIZE;
  const selectedResourceId = positiveInteger(searchParams.get("resource"), 0) || null;

  const updateSearchParams = useCallback((updates: Record<string, string | number | null>, replace = true) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === "") next.delete(key);
      else next.set(key, String(value));
    });
    setSearchParams(next, { replace });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    setSearchDraft(search);
  }, [search]);

  useEffect(() => {
    if (searchDraft === search) return undefined;
    const timeoutId = window.setTimeout(() => {
      updateSearchParams({ search: searchDraft.trim() || null, page: 1, resource: null });
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [search, searchDraft, updateSearchParams]);

  const resourcesQuery = useQuery({
    queryKey: ["resources", "workspace", business?.id, mode, branch, search, resourceType, status, page, pageSize, customFilters],
    queryFn: () => resourcesApi.listPage({
      business: business!.id,
      ...customFilters,
      search: search || undefined,
      resource_type: resourceType,
      resource_group: mode,
      branch,
      status,
      page,
      page_size: pageSize,
    }),
    enabled: Boolean(business?.id),
    placeholderData: keepPreviousData,
  });
  const teamMembersQuery = useQuery({
    queryKey: ["team-members", business?.id],
    queryFn: () => teamApi.allMembers(business!.id),
    enabled: Boolean(business?.id) && hasPermission(user, business?.id, "team", "view"),
  });

  const resourceRows = resourcesQuery.data?.results || [];
  const customTable = useCustomColumns(business?.id || 0, "specialist", resourceRows.filter(item => item.resource_type === "staff").map(item => item.id));
  const totalResources = resourcesQuery.data?.count || 0;
  const totalPages = Math.max(1, Math.ceil(totalResources / pageSize));
  const selectedResourceOnPage = resourceRows.find((resource) => resource.id === selectedResourceId && resource.business === business?.id) || null;
  const selectedResourceQuery = useQuery({
    queryKey: ["resources", "selected", business?.id, selectedResourceId],
    queryFn: async () => {
      const resource = await resourcesApi.get(selectedResourceId!);
      if (resource.business !== business?.id) throw new Error(t("actions.errorForbidden"));
      return resource;
    },
    enabled: Boolean(business?.id && selectedResourceId && !resourcesQuery.isPending && !selectedResourceOnPage),
    retry: false,
  });
  const selectedResource = selectedResourceOnPage || selectedResourceQuery.data || null;
  const activeTeamMembers = (teamMembersQuery.data || []).filter((member) => member.is_active);

  const workingHoursQuery = useQuery({
    queryKey: ["working-hours", "resource-modal", business?.id, selectedResourceId],
    queryFn: () => workingHoursApi.list({ business: business!.id, resource: selectedResourceId! }),
    enabled: Boolean(business?.id && selectedResource),
  });
  const businessHoursQuery = useQuery({
    queryKey: ["working-hours", "resource-create", business?.id],
    queryFn: () => workingHoursApi.list({ business: business!.id }),
    enabled: Boolean(business?.id && createOpen),
  });

  const mutation = useMutation({
    mutationFn: ({ id, payload }: { id?: Id; payload: Partial<Resource> }) =>
      id ? resourcesApi.update({ id, payload }) : resourcesApi.create(payload),
    onSuccess: async (_resource, variables) => {
      await Promise.all(["resources", "branches", "branch-configuration", "branch-catalog", "available-slots"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
      savedRef.current = true;
      setInspectorDirty(false);
      if (variables.id) {
        showNotification({ message: t("resources.noticeSaved"), tone: "success" });
      } else {
        setCreateOpen(false);
        setCreateDirty(false);
        setCreateDraft(undefined);
        updateSearchParams({ resource: _resource.id, search: null, type: null, status: null, page: 1, branch: _resource.resource_type === "staff" ? null : _resource.branch || branch || null });
        setSearchDraft("");
        showNotification({ message: t("resources.noticeCreated"), tone: "success" });
      }
    },
  });
  const resetResourceMutation = mutation.reset;
  useEffect(() => resetResourceMutation(), [selectedResource?.id, createOpen, resetResourceMutation]);

  const statusMutation = useMutation({
    mutationFn: ({ resource, isActive }: { resource: Resource; isActive: boolean }) =>
      resourcesApi.update({ id: resource.id, payload: { is_active: isActive } }),
    onSuccess: async (_resource, variables) => {
      await Promise.all(["resources", "branches", "branch-configuration", "branch-catalog", "available-slots"].map(key => queryClient.invalidateQueries({ queryKey: [key] })));
      showNotification({
        message: t(variables.isActive ? "resources.noticeActivated" : "resources.noticeDeactivated"),
        tone: "success",
      });
    },
    onError: (error) => {
      showNotification({ message: getApiErrorMessage(error), tone: "danger" });
    },
  });
  useEffect(() => {
    if (resourcesQuery.isLoading || resourcesQuery.isFetching) return;
    if (page > totalPages) {
      updateSearchParams({ page: totalPages });
    }
  }, [page, resourcesQuery.isFetching, resourcesQuery.isLoading, totalPages, updateSearchParams]);

  const permissionMessage = permissionForbiddenMessage("settings", "update", t);

  useEffect(() => {
    setPageHeader({ title: t("nav.business") });
    return () => setPageHeader(null);
  }, [setPageHeader, t]);

  const confirmDiscard = useCallback(async () => {
    if (!inspectorDirty) return true;
    const result = await confirmAction({
      title: t("resources.discardChanges"),
      confirmLabel: t("actions.discardChanges"),
      tone: "warning",
    });
    return result.confirmed;
  }, [confirmAction, inspectorDirty, t]);

  const selectResource = useCallback(async (resource: Resource) => {
    if (resource.id === selectedResourceId) return;
    if (!await confirmDiscard()) return;
    setInspectorDirty(false);
    updateSearchParams({ resource: resource.id }, false);
  }, [confirmDiscard, selectedResourceId, updateSearchParams]);

  const closeInspector = useCallback(async () => {
    if (!await confirmDiscard()) return false;
    setInspectorDirty(false);
    updateSearchParams({ resource: null }, false);
    return true;
  }, [confirmDiscard, updateSearchParams]);

  const openSelectedResourceSchedule = useCallback(async () => {
    if (!selectedResource || !await confirmDiscard()) return;
    setInspectorDirty(false);
    navigate(`/app/business/working-hours?view=${selectedResource.resource_type === "staff" ? "staff" : "physical"}&resource=${selectedResource.id}${selectedResource.branch || branch ? `&branch=${selectedResource.branch || branch}` : ""}`);
  }, [branch, confirmDiscard, navigate, selectedResource]);

  const handleResourceRowSelect = useCallback((resource: Resource, _index: number, _interaction: DataTableRowInteraction) => {
    void selectResource(resource);
  }, [selectResource]);

  const deactivateResource = useCallback(async (resource: Resource) => {
    const result = await confirmAction({
      title: t("resources.deactivateTitle"),
      description: t("resources.deactivateDescription", { name: resource.name }),
      confirmLabel: t("resources.actionDeactivate"),
      tone: "warning",
    });
    if (result.confirmed) statusMutation.mutate({ resource, isActive: false });
  }, [confirmAction, statusMutation, t]);

  function openCreate() {
    if (!canManage) return;
    setCreateDraft({ resource_type: mode === "staff" ? "staff" : resourceType || "room", branch: mode === "physical" ? branch : undefined });
    setCreateOpen(true);
  }

  if (!business) return <ErrorState message={t("resources.noBusiness")} />;
  if (resourcesQuery.isLoading || teamMembersQuery.isLoading) return <LoadingState scope="page" />;

  const pageError = resourcesQuery.error || teamMembersQuery.error || (!selectedResourceOnPage && selectedResourceQuery.error);
  const hasFilters = Boolean(search || (mode !== "staff" && resourceType) || status);
  const pageFrom = totalResources === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageTo = Math.min(totalResources, page * pageSize);
  return (
    <>
      <DraftGuard saved={savedRef} dirty={inspectorDirty || createDirty} pending={mutation.isPending} />
      <CrmWorkspacePage edgeToEdge maxWidthClassName="max-w-none" testId={pageError ? undefined : "resources-workspace-ready"}>
        <BusinessWorkspaceNav />
        <BusinessBranchFilter />
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold">{t(mode === "staff" ? "business.staff" : "branches.physicalResources")}</h2>
          {mode === "staff" && hasPermission(user, business.id, "team", "view") && <Button variant="secondary" onClick={() => setAccountsOpen(true)}>{t("business.manageAccounts")}</Button>}
        </div>

        {selectedResourceQuery.isLoading ? <LoadingState /> : null}
        {pageError ? (
          <div className="mb-3 shrink-0">
            <ErrorState
              error={pageError} message={getApiErrorMessage(pageError)}
              action={<Button type="button" variant="secondary" onClick={() => void Promise.all([resourcesQuery.refetch(), teamMembersQuery.refetch(), ...(selectedResourceId && !selectedResourceOnPage ? [selectedResourceQuery.refetch()] : [])])}>{t("common.retry")}</Button>}
            />
          </div>
        ) : null}

        <div data-testid="resources-operational-workspace" className="min-h-[420px] flex-1">
            {customTable.toolbar}
            <DataTable
              className="h-full"
              contentClassName="overscroll-contain"
              rows={resourceRows}
              rowKey={(resource) => resource.id}
              selectedRowKey={selectedResource?.id}
              onRowSelect={handleResourceRowSelect}
              rowAriaLabel={(resource) => t("resources.selectResource", { name: resource.name })}
              rowFocusReturnId={(resource) => `resource-row-${resource.id}`}
              rowTestId={() => "resource-row"}
              tableLabel={t("resources.tableLabel")}
              hideFooter
              emptyTitle={hasFilters ? t("resources.noResultsTitle") : t("resources.emptyTitle")}
              emptyDescription={hasFilters ? t("resources.noResultsText") : t("resources.emptyText")}
              emptyAction={
                hasFilters ? (
                  <Button type="button" variant="secondary" onClick={() => { setSearchDraft(""); updateSearchParams({ search: null, type: null, status: null, page: 1, resource: null }); }}>{t("common.clearAll")}</Button>
                ) : (
                  <Button type="button" variant="secondary" disabled={!canManage} title={!canManage ? permissionMessage : undefined} onClick={openCreate}>
                    <Plus aria-hidden="true" size={16} />{t(mode === "staff" ? "business.addStaff" : "resources.add")}
                  </Button>
                )
              }
              toolbar={
                <ResourcesToolbar
                  searchDraft={searchDraft}
                  resourceType={resourceType}
                  status={status}
                  mode={mode}
                  canManage={canManage}
                  permissionMessage={permissionMessage}
                  isSplitWorkspace={false}
                  shown={resourceRows.length}
                  total={totalResources}
                  page={page}
                  pageSize={pageSize}
                  rangeLabel={t("pagination.range", { from: pageFrom, to: pageTo, total: totalResources })}
                  onSearchChange={setSearchDraft}
                  onResourceTypeChange={(value) => updateSearchParams({ type: value || null, page: 1, resource: null })}
                  onStatusChange={(value) => updateSearchParams({ status: value || null, page: 1, resource: null })}
                  onCreate={openCreate}
                  onPageChange={(nextPage) => updateSearchParams({ page: nextPage, resource: null }, false)}
                  onPageSizeChange={(nextPageSize) => updateSearchParams({ page_size: nextPageSize, page: 1, resource: null })}
                />
              }
              columns={[
                { header: t("resources.name"), className: "max-w-[300px]", cell: (resource) => <span data-testid="resource-name" className="block truncate font-semibold text-platforma-ink">{resource.name}</span> },
                { header: t("resources.type"), cell: (resource) => t(resourceTypeLabelKeys[resource.resource_type]) },
                ...(mode === "staff" ? [{ header: t("resources.linkedUser"), className: "max-w-[220px]", cell: (resource: Resource) => <span className="block truncate">{resource.linked_user_name || resource.linked_user_email || t("resources.noLinkedUser")}</span> }] : []),
                { header: t("resources.bookings"), cell: (resource) => resource.appointment_count || 0 },
                { header: t("appointment.status"), cell: (resource) => <ResourceStatusBadge resource={resource} /> },
                ...customTable.columns,
                {
                  header: t("appointments.actions"),
                  className: "w-16 text-right",
                  cell: (resource) => (
                    <ResourceActionsMenu
                      resource={resource}
                      canManage={canManage}
                      isPending={statusMutation.isPending}
                      onOpen={() => void selectResource(resource)}
                      onActivate={() => statusMutation.mutate({ resource, isActive: true })}
                      onDeactivate={() => void deactivateResource(resource)}
                    />
                  ),
                },
              ]}
            />
        </div>
      </CrmWorkspacePage>

      <ResourceEditModal
        resource={selectedResource}
        businessId={business.id}
        teamMembers={activeTeamMembers}
        workingHours={workingHoursQuery.data || []}
        scheduleLoading={workingHoursQuery.isLoading}
        scheduleError={workingHoursQuery.error ? getApiErrorMessage(workingHoursQuery.error) : undefined}
        canManage={canManage}
        isSaving={mutation.isPending || statusMutation.isPending}
        error={mutation.error}
        onDirtyChange={setInspectorDirty}
        onClose={() => { void closeInspector(); }}
        onOpenSchedule={() => { void openSelectedResourceSchedule(); }}
        onSubmit={(payload) => mutation.mutateAsync({ id: selectedResource!.id, payload })}
      />

      <Modal title={t("business.manageAccounts")} open={accountsOpen} onClose={() => setAccountsOpen(false)}>
        <StaffAccounts businessId={business.id} />
      </Modal>
      <Modal
        title={t(mode === "staff" ? "business.addStaff" : "resources.add")}
        testId="resource-create-modal"
        open={createOpen}
        onClose={async () => {
          if (mutation.isPending) return;
          if (createDirty && !(await confirmAction({ title: t("resources.discardChanges"), confirmLabel: t("actions.discardChanges"), tone: "warning" })).confirmed) return;
          setCreateOpen(false);
          setCreateDirty(false);
          setCreateDraft(undefined);
        }}
      >
        {businessHoursQuery.error ? <ErrorState error={businessHoursQuery.error} message={getApiErrorMessage(businessHoursQuery.error)} /> : null}
        <ResourceCreateForm
          mode={mode}
          onDirtyChange={setCreateDirty}
          submitError={mutation.error}
          businessId={business.id}
          initial={createDraft}
          businessHours={businessHoursQuery.data || []}
          teamMembers={activeTeamMembers}
          disabled={!canManage || businessHoursQuery.isLoading || Boolean(businessHoursQuery.error)}
          onSubmit={(payload) => mutation.mutateAsync({ payload })}
        />
      </Modal>
    </>
  );
}
