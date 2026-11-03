import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { useAuth } from "../../../features/auth/AuthProvider";
import { TaskEditor } from "../../../features/tasks/components/TaskEditor";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { CrmCardPayload } from "../../../types";
import { Button } from "../../ui/Button";
import { StatusBadge } from "../../ui/StatusBadge";
import { drawerSurfaceClass, EmptyBlock } from "./shared";
import type { CrmDrawerEntity } from "./types";

export function EntityTasksPanel({ data, entity }: { data: CrmCardPayload; entity: CrmDrawerEntity }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const cache = useQueryClient();
  const [creating, setCreating] = useState(false);
  const businessId = entity.type === "appointment" ? data.appointment?.business : data.client?.business;
  const canCreate = (entity.type === "client" || entity.type === "appointment") && businessId === business?.id && hasPermission(user, businessId, "tasks", "create");
  return <div className="space-y-3">
    {canCreate ? <Button variant="secondary" onClick={() => setCreating(true)}>{t("taskWorkspace.create")}</Button> : null}
    {creating && canCreate && businessId ? <TaskEditor business={businessId} zone={business?.timezone || "UTC"}
      initialClient={entity.type === "client" ? entity.id : data.client?.id}
      initialAppointment={entity.type === "appointment" ? entity.id : undefined}
      onClose={() => setCreating(false)} onSaved={async () => {
        setCreating(false);
        await Promise.all([cache.invalidateQueries({ queryKey: ["crm-card"] }), cache.invalidateQueries({ queryKey: ["tasks"] })]);
      }} /> : null}
    {data.tasks.map(task => <div key={task.id} className={drawerSurfaceClass}>
      <div className="flex items-center justify-between gap-3">
        <Link className="platforma-focus-ring font-bold text-platforma-ink" to={`/app/tasks/${task.id}`}>{task.title}</Link>
        <StatusBadge status={task.status} />
      </div>
      <p className="mt-1 text-xs text-platforma-muted">{t(`taskWorkspace.priority.${task.priority}`)} · {t("crmCard.deadline")} {formatDateTime(task.due_at, business?.timezone, false, language)}</p>
      {task.description ? <p className="mt-3 text-sm text-platforma-subtle">{task.description}</p> : null}
    </div>)}
    {!data.tasks.length ? <EmptyBlock title={t("crmCard.noTasks")} text={t("crmCard.noTasksText")} /> : null}
    {entity.type === "appointment" && data.meta?.has_more.tasks ? <Link className="platforma-focus-ring text-brand-700" to={`/app/tasks?tab=all&appointment_ids=${entity.id}`}>{t("nav.tasks")}</Link> : null}
  </div>;
}
