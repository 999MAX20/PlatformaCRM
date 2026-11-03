import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";
import { useQuery } from "@tanstack/react-query";
import { Phone } from "lucide-react";
import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { EntityCustomFieldsPanel } from "../../components/crm/drawers/EntityCustomFieldsPanel";

import { appointmentsApi } from "../../api/appointments";
import { getApiErrorMessage } from "../../api/client";
import { crmCardsApi } from "../../api/crmCards";
import { inboxApi } from "../../api/inbox";
import { tasksApi } from "../../api/tasks";
import { ClientForm } from "../../components/forms/ClientForm";
import {
  CrmActionBar,
  EntityWorkspaceEmptyState,
  EntityWorkspaceErrorState,
  EntityWorkspaceAside,
  EntityWorkspaceAvatar,
  EntityWorkspaceBody,
  EntityWorkspaceHeader,
  EntityWorkspaceLoadingState,
  EntityWorkspaceMain,
  EntityWorkspaceMetrics,
  EntityWorkspaceRoot,
} from "../../components/crm";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useClientWorkspaceActions } from "./hooks/useClientWorkspaceActions";
import { PaymentsButton } from "../payments/PaymentsButton";
import {
  ActionPanel,
  AppointmentsList,
  ClientContactPanel,
  ClientWorkspaceMetric,
  ClientWorkspaceSection,
  ConversationsList,
  TasksList,
  TimelineList,
  clientWorkspaceIcons,
} from "./components/ClientWorkspaceSections";

const RELATED_PAGE_SIZE = 8;
const supportedClientActionIds = new Set([
  "create_appointment",
  "create_task",
]);

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
    appointmentsQuery.error ||
    tasksQuery.error ||
    conversationsQuery.error;
  const isLoading =
    cardQuery.isLoading ||
    appointmentsQuery.isLoading ||
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
  if (pageError)
    return (
      <EntityWorkspaceErrorState message={getApiErrorMessage(pageError)} />
    );
  if (!client) {
    return (
      <EntityWorkspaceEmptyState
        title={t("clients.notFoundTitle")}
        description={t("clients.notFoundText")}
      />
    );
  }

  const counts = card?.meta?.related_counts;
  const executableActions = (card.available_action_details || []).filter(
    (action) => supportedClientActionIds.has(action.id),
  );

  return (
    <>
      <EntityWorkspaceRoot>
        <EntityWorkspaceHeader
          backLabel={t("common.back")}
          onBack={() => navigate("/app/clients")}
          avatar={
            <EntityWorkspaceAvatar>
              {client.full_name.slice(0, 2).toUpperCase()}
            </EntityWorkspaceAvatar>
          }
          title={client.full_name}
          subtitle={client.phone || client.email || t("clients.noContacts")}
          actions={
            <>
              <PaymentsButton client={client} />
              <Button
                data-testid="client-edit-action"
                type="button"
                variant="secondary"
                onClick={() => actions.setEditOpen(true)}
                disabled={actions.saveClientMutation.isPending}
              >
                {t("clients.edit")}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => actions.setTagOpen(true)}
                disabled={actions.addTagMutation.isPending}
              >
                {t("clients.addTag")}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate("/app/clients")}
              >
                {t("nav.clients")}
              </Button>
              <Button
                type="button"
                disabled={!client.phone}
                onClick={() =>
                  client.phone &&
                  window.open(`tel:${client.phone.replace(/\D/g, "")}`, "_self")
                }
              >
                <Phone size={16} />
                {t("clients.call")}
              </Button>
              <Button
                type="button"
                variant="warning"
                isLoading={actions.archiveMutation.isPending}
                onClick={() => void actions.requestArchiveClient(client)}
              >
                {t("clients.archiveAction")}
              </Button>
            </>
          }
        />

        <EntityWorkspaceMetrics>
          <ClientWorkspaceMetric
            label={t("clients.metricBookings")}
            value={counts?.appointments ?? related.appointments.length}
          />
          <ClientWorkspaceMetric
            label={t("clients.metricDialogs")}
            value={counts?.conversations ?? related.conversations.length}
          />
          <ClientWorkspaceMetric
            label={t("clients.activeTasks")}
            value={counts?.tasks ?? related.tasks.length}
          />
        </EntityWorkspaceMetrics>

        <EntityWorkspaceBody>
          <EntityWorkspaceAside>
            <ClientWorkspaceSection
              title={t("clients.contacts")}
              icon={clientWorkspaceIcons.contacts}
            >
              <ClientContactPanel client={client} />
            </ClientWorkspaceSection>
            <ClientWorkspaceSection
              title={t("clients.tagsAndNotes")}
              icon={clientWorkspaceIcons.tags}
            >
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {card.tags.length ? (
                    card.tags.map((tag) => (
                      <span
                        key={tag.id}
                        className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700"
                      >
                        {tag.tag_name || t("clients.tag")}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm font-semibold text-platforma-faint">
                      {t("clients.noTagsYet")}
                    </span>
                  )}
                </div>
                {client.notes ? (
                  <p className="rounded-control bg-surface-muted p-3 text-sm font-medium leading-6 text-platforma-subtle">
                    {client.notes}
                  </p>
                ) : null}
              </div>
            </ClientWorkspaceSection>
            <ClientWorkspaceSection
              title={t("clients.quickActions")}
              icon={clientWorkspaceIcons.actions}
            >
              {executableActions.length ? (
                <CrmActionBar
                  actions={executableActions}
                  onExecute={(action) => {
                    if (action.id === "create_appointment")
                      navigate(`/app/appointments?create=1&client=${client.id}`);
                    if (action.id === "create_task")
                      navigate(`/app/tasks?create=1&client=${client.id}`);
                  }}
                />
              ) : (
                <ActionPanel actions={executableActions} />
              )}
            </ClientWorkspaceSection>
          </EntityWorkspaceAside>

          <EntityWorkspaceMain>
            {card?.custom_fields.length ? <div className="lg:col-span-2"><EntityCustomFieldsPanel data={card} entity={{ type: "client", id: client.id }} /></div> : null}
            <ClientWorkspaceSection
              title={t("nav.tasks")}
              icon={clientWorkspaceIcons.tasks}
            >
              <TasksList tasks={related.tasks} />
            </ClientWorkspaceSection>
            <ClientWorkspaceSection
              title={t("appointments.title")}
              icon={clientWorkspaceIcons.appointments}
            >
              <AppointmentsList appointments={related.appointments} />
              {hasPermission(user, business?.id, "appointments", "view") ? <Link className="platforma-focus-ring inline-flex rounded py-2 text-brand-700" to={`/app/appointments?view=plans&client=${client.id}`}>{t("plans.title")}</Link> : null}
                {counts && counts.appointments > related.appointments.length ? <Link className="platforma-focus-ring text-brand-700" to={`/app/appointments?client=${client.id}`}>{t("appointments.title")} ({counts.appointments})</Link> : null}
            </ClientWorkspaceSection>
            <ClientWorkspaceSection
              title={t("crmCard.messages")}
              icon={clientWorkspaceIcons.conversations}
              className="lg:col-span-2"
            >
              <ConversationsList conversations={related.conversations} />
            </ClientWorkspaceSection>
            <ClientWorkspaceSection
              title={t("crmCard.timeline")}
              icon={clientWorkspaceIcons.timeline}
              className="lg:col-span-2"
            >
              <TimelineList cardTimeline={card.timeline} />
            </ClientWorkspaceSection>
          </EntityWorkspaceMain>
        </EntityWorkspaceBody>
      </EntityWorkspaceRoot>

      <Modal
        title={t("clients.editTitle")}
        open={actions.editOpen}
        onClose={() => actions.setEditOpen(false)}
      >
        {actions.business?.id ? (
          <ClientForm
            businessId={actions.business.id}
            initial={client}
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
        open={actions.tagOpen}
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
