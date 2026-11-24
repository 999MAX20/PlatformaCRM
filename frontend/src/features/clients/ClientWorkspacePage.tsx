import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ClientReferenceView } from "./components/ClientReferenceView";

import { appointmentsApi } from "../../api/appointments";
import { normalizeAppError } from "../../api/appError";
import { crmCardsApi } from "../../api/crmCards";
import { inboxApi } from "../../api/inbox";
import { tasksApi } from "../../api/tasks";
import { ClientForm } from "../../components/forms/ClientForm";
import { EntityWorkspaceEmptyState, EntityWorkspaceErrorState, EntityWorkspaceLoadingState } from "../../components/crm";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { dateInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useClientWorkspaceActions } from "./hooks/useClientWorkspaceActions";
import { useUnsavedEntryWarning } from "../auth/useUnsavedEntryWarning";
import { useRestoreClient } from "./hooks/useRestoreClient";
const RELATED_PAGE_SIZE = 8;

function asNumericId(value: string | undefined): number | null {
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

export function ClientWorkspacePage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { id: routeId } = useParams();
  const clientId = asNumericId(routeId);
  const actions = useClientWorkspaceActions(clientId);
  const restoreClient = useRestoreClient();
  const [editState, setEditState] = useState({ dirty: false, pending: false });
  useUnsavedEntryWarning(editState.dirty || editState.pending);
  const closeEdit = () => { if (!editState.pending && (!editState.dirty || window.confirm(t("medical.clinical.discard")))) actions.setEditOpen(false); };

  const cardQuery = useQuery({
    queryKey: ["crm-card", "client", clientId, business?.id, user?.id],
    queryFn: () => crmCardsApi.get({ type: "client", id: clientId as number, business: business?.id }),
    enabled: Boolean(clientId && business),
  });
  const appointmentsQuery = useQuery({
    queryKey: ["appointments", "client-workspace", clientId, business?.id, user?.id],
    queryFn: () =>
      appointmentsApi.list({
        business: business?.id,
        client_ids: String(clientId),
        page_size: RELATED_PAGE_SIZE,
      }),
    enabled: Boolean(clientId && business && hasPermission(user, business.id, "appointments", "view")),
  });
  const nextAppointmentQuery = useQuery({
    queryKey: ["appointments", "client-next", clientId, business?.id, user?.id],
    enabled: Boolean(clientId && business && hasPermission(user, business.id, "appointments", "view")),
    queryFn: async () => {
      const now = Date.now();
      for (let page = 1; ; page += 1) {
        const result = await appointmentsApi.workspace({ business: business!.id, client: clientId!, workflow: "planned",
          start_from: dateInTimeZone(new Date(now - 86400000).toISOString(), business!.timezone), ordering: "start_at", page, page_size: 100 });
        const next = result.results.find(item => Date.parse(item.end_at) >= now);
        if (next || !result.next) return next ?? null;
      }
    },
  });
  const tasksQuery = useQuery({
    queryKey: ["tasks", "client-workspace", clientId, business?.id, user?.id],
    queryFn: () =>
      tasksApi.listPage({
        business: business?.id,
        client_ids: String(clientId),
        page_size: RELATED_PAGE_SIZE,
        status: "active",
      }),
    enabled: Boolean(clientId && business && hasPermission(user, business.id, "tasks", "view")),
  });
  const conversationsQuery = useQuery({
    queryKey: ["inbox-conversations", "client-workspace", clientId, business?.id, user?.id],
    queryFn: () => inboxApi.listConversations({ client_ids: String(clientId) }),
    enabled: Boolean(clientId && business && hasPermission(user, business.id, "conversations", "view")),
  });

  const pageError =
    cardQuery.error ||
    appointmentsQuery.error || nextAppointmentQuery.error ||
    tasksQuery.error ||
    conversationsQuery.error;
  const isLoading =
    cardQuery.isLoading ||
    appointmentsQuery.isLoading ||
    nextAppointmentQuery.isLoading ||
    tasksQuery.isLoading ||
    conversationsQuery.isLoading;
  const card = cardQuery.data;
  const client = card?.client;
  const related = useMemo(
    () => ({
      appointments: appointmentsQuery.data || card?.appointments || [],
      conversations:
        conversationsQuery.data?.results || card?.conversations || [],
      tasks: tasksQuery.data?.results || card?.tasks || [],
    }),
    [
      appointmentsQuery.data,
      card,
      conversationsQuery.data,
      tasksQuery.data,
    ],
  );

  if (!clientId)
    return <EntityWorkspaceErrorState message={t("clients.notFoundTitle")} />;
  if (isLoading) return <EntityWorkspaceLoadingState />;
  if (pageError && (!cardQuery.data || ["authentication", "permission", "not_found"].includes(normalizeAppError(pageError).category)))
    return (
      <ErrorState error={pageError} action={<Button variant="secondary" onClick={() => { void cardQuery.refetch(); void appointmentsQuery.refetch(); if (nextAppointmentQuery.isEnabled) void nextAppointmentQuery.refetch(); if (tasksQuery.isEnabled) void tasksQuery.refetch(); if (conversationsQuery.isEnabled) void conversationsQuery.refetch(); }}>{t("common.retry")}</Button>} />
    );
  if (!client) {
    return (
      <EntityWorkspaceEmptyState
        title={t("clients.notFoundTitle")}
        description={t("clients.notFoundText")}
      />
    );
  }

  const canEdit = !client.is_archived && card.available_action_details?.some(action => action.id === "add_note" && action.allowed) === true;
  const canArchive = hasPermission(user, client.business, "clients", "delete");

  return (
    <>
      {pageError && <ErrorState error={pageError} action={<Button variant="secondary" onClick={() => { void cardQuery.refetch(); void appointmentsQuery.refetch(); if (nextAppointmentQuery.isEnabled) void nextAppointmentQuery.refetch(); if (tasksQuery.isEnabled) void tasksQuery.refetch(); if (conversationsQuery.isEnabled) void conversationsQuery.refetch(); }}>{t("common.retry")}</Button>} />}
      <ClientReferenceView key={`${business?.id}:${client.id}:${user?.id}`}
        editState={editState} client={client} card={{ ...card, tasks: related.tasks, conversations: related.conversations }}
        appointments={related.appointments} upcoming={nextAppointmentQuery.error ? undefined : nextAppointmentQuery.data ?? undefined} timeZone={business?.timezone || "Asia/Almaty"}
        userId={Number(user?.id)} medical={!client.is_archived && user?.capabilities?.[String(business?.id)]?.modules?.medical_records === true}
        canEdit={canEdit} canBook={!client.is_archived && hasPermission(user, business?.id, "appointments", "create")}
        onEdit={() => actions.setEditOpen(true)} onTag={() => actions.setTagOpen(true)}
        extraActions={<>
          {hasPermission(user, business?.id, "tasks", "create") && <Button variant="secondary" onClick={() => navigate(`/app/tasks?create=1&client=${client.id}`)}>{t("taskWorkspace.create")}</Button>}
          {canArchive && (client.is_archived
            ? <Button variant="secondary" isLoading={restoreClient.isPending} onClick={() => void restoreClient.restore(client)}>{t("clients.restoreAction")}</Button>
            : <Button variant="warning" isLoading={actions.archiveMutation.isPending} onClick={() => void actions.requestArchiveClient(client)}>{t("clients.archiveAction")}</Button>)}
        </>}
      />

      <Modal
        title={t("clients.editTitle")}
        open={actions.editOpen && canEdit}
        onClose={closeEdit}
      >
        {actions.business?.id ? (
          <ClientForm
            businessId={actions.business.id}
            initial={client}
            onStateChange={setEditState}
            onSubmit={(payload) =>
              actions.saveClientMutation.mutateAsync(payload)
            }
            onOpenClient={(id) => {
              actions.setEditOpen(false);
              navigate(`/app/clients/${id}`);
            }}
          />
        ) : (
          <ErrorState message={t("account.businessRequired")} />
        )}
      </Modal>

      <Modal
        title={t("clients.addTag")}
        open={actions.tagOpen && canEdit}
        onClose={() => actions.setTagOpen(false)}
      >
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const tagName = actions.tagDraft.trim();
            if (!tagName) return;
            actions.addTagMutation.mutate({ tagName });
          }}
        >
          <Input
            label={t("clients.tagPrompt")}
            value={actions.tagDraft}
            onChange={(event) => actions.setTagDraft(event.target.value)}
            required
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => actions.setTagOpen(false)}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              isLoading={actions.addTagMutation.isPending}
              disabled={!actions.tagDraft.trim()}
            >
              {t("clients.addTag")}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
