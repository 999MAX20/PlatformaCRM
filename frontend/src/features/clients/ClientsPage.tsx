import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { Button } from "../../components/ui/Button";
import { useNavigate } from "react-router";
import { hasPermission } from "../../lib/permissions";
import palette from "../../theme/semantic-tokens.json";

import { clientsApi, type ClientMergeDryRun } from "../../api/clients";
import { getApiErrorMessage } from "../../api/client";
import {
  segmentFiltersApi,
  segmentsApi,
  taggedObjectsApi,
  tagsApi,
} from "../../api/activities";
import { CrmEntityDrawer } from "../../components/crm/CrmEntityDrawer";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { useUndoToast } from "../../components/actions/UndoToastProvider";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import type { Client, Id } from "../../types";
import { ClientsFilters } from "./components/ClientsFilters";
import { ClientsModals } from "./components/ClientsModals";
import { ClientsTable } from "./components/ClientsTable";
import { useCustomColumns } from "../../components/crm/CustomFieldColumns";
import { useClientsPageHeader } from "./hooks/useClientsPageHeader";
import { useClientsWorkspace } from "./hooks/useClientsWorkspace";
export function ClientsPage() {
  const { t } = useI18n();
  const confirmAction = useActionConfirm();
  const showUndoToast = useUndoToast();
  const queryClient = useQueryClient();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const navigate = useNavigate();
  const openPayments = useCallback(() => { void navigate("/app/payments"); }, [navigate]);
  const [mergePreview, setMergePreview] = useState<ClientMergeDryRun | null>(
    null,
  );
  const {
    ordering,
    hasFilters: hasClientFilters,
    setOrdering,
    clearAllFilters,
    clearCreateParam,
    closeClientCard,
    createOpen,
    drawerEntity,
    editing,
    filteredClients,
    openClientCard,
    openCreateClient,
    openEditClient,
    pageLoading,
    rows,
    segmentDraft,
    segmentOpen,
    segments,
    selectedClient,
    setActionClient,
    setCreateOpen,
    setEditing,
    setSegmentDraft,
    setSegmentOpen,
    setSelectedClientId,
    setTagDraft,
    setTagOpen,
    source,
    sourceOptions,
    tagDraft,
    tagList,
    tagOpen,
    tagOptions,
    taggedObjects,
    tagsQuery,
    toggleClientColumn,
    visibleClientColumns,
  } = useClientsWorkspace({
    businessId: business?.id,
    currentUserId: user?.id || null,
    t,
  });

  const canCreate = hasPermission(user, business?.id, "clients", "create");
  const customTable = useCustomColumns(business?.id || 0, "client", rows.map(row => row.client.id));
  useClientsPageHeader({
    t,
    onCreateClient: canCreate ? openCreateClient : undefined,
    onCloseClientCard: closeClientCard,
    onPayments: hasPermission(user, business?.id, "payments") ? openPayments : undefined,
  });

  const saveClientMutation = useMutation({
    mutationFn: (payload: Partial<Client>) =>
      editing
        ? clientsApi.update({ id: editing.id, payload })
        : clientsApi.create(payload),
    onSuccess: (client) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({
        queryKey: ["crm-card", "client", client.id],
      });
      setCreateOpen(false);
      setEditing(undefined);
      openClientCard(client.id);
      clearCreateParam();
    },
  });

  const resetClientMutation = saveClientMutation.reset;
  useEffect(() => resetClientMutation(), [createOpen, editing?.id, resetClientMutation]);

  const mergeMutation = useMutation({
    mutationFn: ({
      targetId,
      duplicateId,
    }: {
      targetId: number;
      duplicateId: number;
    }) => clientsApi.merge({ id: targetId, duplicate_client_id: duplicateId }),
    onSuccess: (mergedClient) => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({
        queryKey: ["crm-card", "client", mergedClient.target_client_id],
      });
      setCreateOpen(false);
      setEditing(undefined);
      setMergePreview(null);
    },
  });
  const mergeDryRunMutation = useMutation({
    mutationFn: ({
      targetId,
      duplicateId,
    }: {
      targetId: number;
      duplicateId: number;
    }) =>
      clientsApi.mergeDryRun({
        id: targetId,
        duplicate_client_id: duplicateId,
      }),
    onSuccess: (preview) => setMergePreview(preview),
  });

  const archiveMutation = useMutation({
    mutationFn: clientsApi.archive,
    onSuccess: async (_archivedClient, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["clients"] });
      await queryClient.invalidateQueries({
        queryKey: ["crm-card", "client", variables.id],
      });
      setActionClient(null);
      showUndoToast({
        message: t("clients.noticeArchived"),
        onRecover: async () => {
          await queryClient.invalidateQueries({ queryKey: ["clients"] });
          await queryClient.invalidateQueries({ queryKey: ["crm-card", "client", variables.id] });
        },
        onUndo: async () => {
          await clientsApi.restore(variables.id);
          await queryClient.invalidateQueries({ queryKey: ["clients"] });
          await queryClient.invalidateQueries({
            queryKey: ["crm-card", "client", variables.id],
          });
        },
      });
    },
  });

  const addTagMutation = useMutation({
    mutationFn: async ({
      clientId,
      tagName,
    }: {
      clientId: Id;
      tagName: string;
    }) => {
      const existing = tagList.find(
        (tag) => tag.name.toLowerCase() === tagName.toLowerCase(),
      );
      const tag =
        existing ||
        (await tagsApi.create({
          business: business!.id,
          name: tagName,
          color: palette.tokens["brand.default"],
          source: "manual",
        }));
      return taggedObjectsApi.create({
        business: business!.id,
        tag: tag.id,
        entity_type: "client",
        entity_id: String(clientId),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      queryClient.invalidateQueries({ queryKey: ["tagged-objects"] });
      queryClient.invalidateQueries({ queryKey: ["crm-card"] });
      setTagOpen(false);
      setTagDraft("");
      setActionClient(null);
    },
  });

  const createSegmentMutation = useMutation({
    mutationFn: async () => {
      const segment = await segmentsApi.create({
        business: business!.id,
        name: segmentDraft.name,
        description: segmentDraft.name,
        entity_type: "client",
        is_active: true,
      });
      await segmentFiltersApi.create({
        business: business!.id,
        segment: segment.id,
        field: segmentDraft.field,
        operator: segmentDraft.operator,
        value_json: { value: segmentDraft.value },
        sort_order: 1,
      });
      await segmentsApi.refreshCount(segment.id);
      return segment;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["segments"] });
      setSegmentDraft({
        name: "",
        field: "source",
        operator: "equals",
        value: "",
      });
      setSegmentOpen(false);
    },
  });

  async function requestArchiveClient(client: Client) {
    const result = await confirmAction({
      title: t("clients.archiveClient"),
      description: t("clients.archiveConfirmText", {
        name: client.full_name || t("common.client"),
      }),
      confirmLabel: t("clients.archiveAction"),
      tone: "warning",
      reason: {
        label: t("clients.archiveReason"),
        placeholder: t("clients.archiveReasonPlaceholder"),
        required: true,
        minLength: 3,
      },
    });
    if (!result.confirmed || !result.reason) return;
    setActionClient(client);
    setSelectedClientId(client.id);
    archiveMutation.mutate({ id: client.id, reason: result.reason });
  }

  const pageError =
    filteredClients.error ||
    tagsQuery.error ||
    segments.error ||
    taggedObjects.error ||
    mergeDryRunMutation.error ||
    mergeMutation.error ||
    archiveMutation.error ||
    addTagMutation.error ||
    createSegmentMutation.error;

  if (!business) return <ErrorState message={t("clients.noBusiness")} />;
  if (pageLoading) return <LoadingState scope="page" />;

  return (
    <>
      <div className="space-y-4 pt-2" data-testid="clients-workspace-ready" aria-busy={filteredClients.isFetching}>
        {hasPermission(user, business.id, "payments") && <div className="flex justify-end lg:hidden">
          <Button variant="secondary" onClick={openPayments} data-focus-return-id="clients-payments">{t("payments.title")}</Button>
        </div>}
        <ClientsFilters key={`${business.id}:${user?.id}`}
            tagOptions={tagOptions} sourceOptions={sourceOptions}
          counts={filteredClients.isError || filteredClients.isPlaceholderData ? undefined : filteredClients.data?.summary}
          visibleColumns={visibleClientColumns} onToggleColumn={toggleClientColumn}
            customTable={customTable} t={t} />
        {pageError && <ErrorState error={pageError} message={getApiErrorMessage(pageError)} action={<Button variant="secondary" onClick={() => { void Promise.all([filteredClients.refetch(), tagsQuery.refetch(), segments.refetch(), taggedObjects.refetch()]); }}>{t("common.retry")}</Button>} />}
        {customTable.error}
        {!filteredClients.isError && <ClientsTable rows={rows} ordering={ordering} onOrderingChange={setOrdering}
          onOpenClient={openClientCard}
          hasFilters={hasClientFilters} onResetFilters={clearAllFilters} onCreateClient={canCreate ? openCreateClient : undefined}
          visibleColumns={visibleClientColumns} customColumns={customTable.columns} t={t} />}
      </div>

      <ClientsModals
        protectDrafts={drawerEntity?.type === "client"}
        saveError={saveClientMutation.error}
        businessId={business.id}
        createOpen={createOpen && canCreate}
        editing={editing}
        mergePreview={mergePreview}
        mergeMutation={mergeMutation}
        mergeDryRunMutation={mergeDryRunMutation}
        tagOpen={tagOpen}
        tagDraft={tagDraft}
        selectedClient={selectedClient}
        addTagMutation={addTagMutation}
        segmentOpen={segmentOpen}
        segmentDraft={segmentDraft}
        tagList={tagList}
        createSegmentMutation={createSegmentMutation}
        t={t}
        onCloseCreate={() => {
          saveClientMutation.reset();
          setCreateOpen(false);
          setEditing(undefined);
          clearCreateParam();
        }}
        onCreateSubmit={(payload) => saveClientMutation.mutateAsync(payload)}
        onOpenClient={(id) => {
          setCreateOpen(false);
          setEditing(undefined);
          openClientCard(id);
        }}
        onCloseMergePreview={() => setMergePreview(null)}
        onCloseTag={() => {
          setTagOpen(false);
          setTagDraft("");
        }}
        onTagDraftChange={setTagDraft}
        onSegmentDraftChange={setSegmentDraft}
        onCloseSegment={() => setSegmentOpen(false)}
      />

      <CrmEntityDrawer
        entity={drawerEntity}
        onClose={closeClientCard}
        clientActions={{
          onEdit: openEditClient,
          onAddTag: (client) => {
            setActionClient(client);
            setSelectedClientId(client.id);
            setTagOpen(true);
          },
          onArchive: (client) => {
            void requestArchiveClient(client);
          },
        }}
      />
    </>
  );
}
