import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../../features/auth/AuthProvider";

import { crmCardsApi } from "../../api/crmCards";
import { cn } from "../../lib/cn";
import { useI18n } from "../../lib/i18n";
import { AppointmentDrawerContent } from "./drawers/appointment";
import { ClientDrawerContent } from "./drawers/client";
import { GenericDrawerContent } from "./drawers/fallback";
import { EntityAttachmentsPanel } from "./drawers/EntityAttachmentsPanel";
import { EntityAppointmentsPanel } from "./drawers/EntityAppointmentsPanel";
import { EntityConversationsPanel } from "./drawers/EntityConversationsPanel";
import { EntityDealsPanel } from "./drawers/EntityDealsPanel";
import { EntityNotesPanel } from "./drawers/EntityNotesPanel";
import { EntityTasksPanel } from "./drawers/EntityTasksPanel";
import { EntityTimeline } from "./drawers/EntityTimeline";
import { CrmEntityHeader, CrmEntityTabs } from "./drawers/shell";
import type { CrmCardTab, CrmDrawerEntity } from "./drawers/types";
import { Drawer } from "../ui/Overlay";
import { ErrorState, LoadingState } from "../ui/StateViews";
import type { Client } from "../../types";

export type { CrmCardTab, CrmDrawerEntity } from "./drawers/types";

type TabId = CrmCardTab;
export type ClientDrawerActions = {
  onEdit?: (client: Client) => void;
  onAddTag?: (client: Client) => void;
  onArchive?: (client: Client) => void;
};

export function CrmEntityDrawer({
  entity,
  onClose,
  clientActions,
}: {
  entity: CrmDrawerEntity | null;
  onClose: () => void;
  clientActions?: ClientDrawerActions;
}) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const historical = entity?.type === "lead" || entity?.type === "deal";
  const [activeTab, setActiveTab] = useState<TabId>(entity?.initialTab || "overview");
  const [isOpen, setIsOpen] = useState(false);
  const titleId = "crm-entity-drawer-title";
  const query = useQuery({
    queryKey: ["crm-card", entity?.type, entity?.id, business?.id, user?.id],
    queryFn: () => crmCardsApi.get({ type: entity!.type, id: entity!.id, business: business?.id }),
    enabled: Boolean(entity && business),
  });
  const data = query.data;
  useEffect(() => {
    setActiveTab(entity?.initialTab || "overview");
  }, [entity?.id, entity?.initialTab, entity?.type]);
  useEffect(() => {
    if (!entity) {
      setIsOpen(false);
      return;
    }
    setIsOpen(false);
    const frame = requestAnimationFrame(() => setIsOpen(true));
    return () => {
      cancelAnimationFrame(frame);
      setIsOpen(false);
    };
  }, [entity?.id, entity?.type]);
  const tabContent = useMemo(() => {
    if (!data) return null;
    if (historical) return <div className="space-y-4">
      <Link className="platforma-focus-ring text-brand-700" to={`/app/${entity!.type === "lead" ? "leads" : "deals"}/${entity!.id}`} onClick={onClose}>{t("records.legacyTitle")}</Link>
      <EntityTimeline data={data} />
      <EntityAttachmentsPanel data={data} entity={entity!} readOnly />
    </div>;
    if (activeTab === "timeline") return <EntityTimeline data={data} />;
    if (activeTab === "tasks") return <EntityTasksPanel key={`${entity!.type}:${entity!.id}`} data={data} entity={entity!} />;
    if (activeTab === "appointments") return <EntityAppointmentsPanel data={data} />;
    if (activeTab === "deals") return <EntityDealsPanel data={data} />;
    if (activeTab === "files") return <EntityAttachmentsPanel data={data} entity={entity!} />;
    if (activeTab === "messages") return <EntityConversationsPanel data={data} />;
    if (activeTab === "notes") return <EntityNotesPanel data={data} entity={entity!} />;
    if (entity?.type === "appointment") return <AppointmentDrawerContent data={data} entity={entity} />;
    if (entity?.type === "client") return <ClientDrawerContent data={data} entity={entity} actions={clientActions} />;
    return <GenericDrawerContent data={data} entity={entity!} />;
  }, [activeTab, clientActions, data, entity, historical, onClose, t]);

  if (!entity) return null;

  return (
    <Drawer
      open={Boolean(entity)}
      onClose={onClose}
      titleId={titleId}
      testId="crm-entity-drawer"
      className={cn(
        "transition-transform duration-[620ms] ease-[cubic-bezier(0.16,1,0.3,1)] will-change-transform",
        isOpen ? "translate-x-0" : "translate-x-full",
      )}
    >
      <CrmEntityHeader data={data} entity={entity} titleId={titleId} onClose={onClose} />
      {!historical ? <CrmEntityTabs active={activeTab} onChange={setActiveTab} data={data} /> : null}
      <div
        className="min-h-0 flex-1 overflow-y-auto px-5 pb-8 sm:px-7"
        data-testid="crm-entity-drawer-content"
      >
        {query.isLoading ? <LoadingState /> : null}
        {query.error ? <ErrorState message={t("crmCard.loadError")} /> : null}
        {tabContent}
      </div>
    </Drawer>
  );
}
