import { useLeadCardQueue } from "../../../features/leads/hooks/useLeadCardQueue";
import { LeadOfflineQueueStatus } from "../../../features/leads/components/LeadOfflineQueueStatus";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { leadsApi } from "../../../api/leads";
import { tasksApi } from "../../../api/tasks";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { Button } from "../../ui/Button";
import { Input } from "../../ui/Input";
import { StatusBadge } from "../../ui/StatusBadge";
import { ErrorState } from "../../ui/StateViews";
import { drawerSurfaceClass, EmptyBlock } from "./shared";

export function EntityTasksPanel({ data }: { data: CrmCardPayload }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [taskTitle, setTaskTitle] = useState("");
  const businessId = data.client?.business || data.lead?.business || data.deal?.business || data.appointment?.business;
  const offline = useLeadCardQueue(data.lead?.business);
  const mutation = useMutation({
    networkMode: data.lead ? "always" : "online",
    mutationFn: async () => {
      if (!businessId || !taskTitle.trim()) throw new Error("Task title is required.");
      if (data.lead && !navigator.onLine) {
        await offline.enqueueOfflineAction({ id: crypto.randomUUID(), type: "task", leadId: data.lead.id,
          title: taskTitle.trim(), due_at: "", assignee: "", priority: "normal", createdAt: new Date().toISOString() });
        return;
      }
      if (data.lead) return leadsApi.createTask({ leadId: data.lead.id, payload: { title: taskTitle.trim(), priority: "normal", assignee: null, due_at: null } });
      return tasksApi.create({
        business: businessId,
        title: taskTitle.trim(),
        client: data.client?.id || null,
        lead: null,
        deal: data.deal?.id || null,
        appointment: data.appointment?.id || null,
        priority: "normal",
      });
    },
    onSuccess: () => {
      setTaskTitle("");
      queryClient.invalidateQueries({ queryKey: ["crm-card"] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return (
    <div className="space-y-3">
      <LeadOfflineQueueStatus queue={offline.offlineQueue} recover={offline.recoverOfflineAction} storageError={offline.storageError} syncing={offline.syncing} online={offline.isOnline} />
      <div className={drawerSurfaceClass}>
        <h3 className="font-semibold text-platforma-ink">{t("crmCard.quickTask")}</h3>
        <p className="mt-1 text-sm leading-6 text-platforma-muted">{t("crmCard.quickTaskText")}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto]">
          <Input value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder={t("crmCard.taskPlaceholder")} />
          <Button type="button" variant="secondary" isLoading={mutation.isPending} onClick={() => mutation.mutate()}>
            {t("crmCard.createTask")}
          </Button>
        </div>
        {mutation.error ? <div className="mt-2"><ErrorState message={t("crmCard.taskError")} /></div> : null}
      </div>
      {data.tasks.map((task) => (
        <div key={task.id} className={drawerSurfaceClass}>
          <div className="flex items-center justify-between gap-3">
            <p className="font-bold text-platforma-ink">{task.title}</p>
            <StatusBadge status={task.status} />
          </div>
          <p className="mt-1 text-xs text-platforma-muted">{task.priority} · {t("crmCard.deadline")} {formatDateTime(task.due_at)}</p>
          {task.description ? <p className="mt-3 text-sm leading-6 text-platforma-subtle">{task.description}</p> : null}
        </div>
      ))}
      {!data.tasks.length ? <EmptyBlock title={t("crmCard.noTasks")} text={t("crmCard.noTasksText")} /> : null}
    </div>
  );
}
