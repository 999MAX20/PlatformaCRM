import { AlertTriangle, CheckCircle2, Clock3, UserRound } from "lucide-react";

import type { TaskWorkloadItem, TaskWorkloadResponse } from "../../../api/tasks";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";

type TaskWorkloadPanelProps = {
  workload?: TaskWorkloadResponse;
  selectedAssignee: string;
  onSelectAssignee: (value: string) => void;
};

export function TaskWorkloadPanel({ workload, selectedAssignee, onSelectAssignee }: TaskWorkloadPanelProps) {
  const { t } = useI18n();
  if (!workload) return null;

  return (
    <section className="overflow-hidden rounded-card border border-platforma-border bg-surface-card shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-platforma-border px-4 py-3">
        <div>
          <h2 className="text-sm font-bold text-platforma-text">{t("tasks.workloadTitle")}</h2>
          <p className="mt-1 text-sm font-semibold text-platforma-muted">
            {t("tasks.workloadActiveCount", { count: workload.totals.active_tasks })} · {t("tasks.workloadAssigneeCount", { count: workload.totals.assignees })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <WorkloadTotal label={t("tasks.workloadOverdue")} value={workload.totals.overdue} tone="red" />
          <WorkloadTotal label={t("tasks.workloadToday")} value={workload.totals.due_today} tone="amber" />
          <WorkloadTotal label={t("tasks.workloadPriority")} value={workload.totals.high_priority} tone="brand" />
        </div>
      </div>
      <div className="grid gap-2 p-3 md:grid-cols-2 xl:grid-cols-4">
        {workload.items.map((item) => (
          <WorkloadAssigneeCard
            key={`${item.type}-${item.user_id || "unassigned"}`}
            item={item}
            selectedAssignee={selectedAssignee}
            onSelectAssignee={onSelectAssignee}
          />
        ))}
      </div>
    </section>
  );
}

function WorkloadAssigneeCard({
  item,
  selectedAssignee,
  onSelectAssignee,
}: {
  item: TaskWorkloadItem;
  selectedAssignee: string;
  onSelectAssignee: (value: string) => void;
}) {
  const { t } = useI18n();
  const assigneeValue = item.user_id ? String(item.user_id) : "unassigned";
  const isSelected = selectedAssignee === assigneeValue;
  const title = item.type === "unassigned" ? t("tasks.noAssignee") : item.name || item.email || t("tasks.noAssignee");

  return (
    <button
      type="button"
      className={`min-h-[168px] rounded-lg border p-4 text-left transition ${
        isSelected ? "border-brand-100 bg-brand-50 shadow-sm" : "border-platforma-border bg-surface-muted hover:border-brand-200 hover:bg-platforma-card"
      }`}
      onClick={() => onSelectAssignee(isSelected ? "" : assigneeValue)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${item.type === "unassigned" ? "bg-[var(--platforma-warning-soft)] text-platforma-warning" : "bg-brand-50 text-brand-700"}`}>
            <UserRound size={18} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-bold text-platforma-text">{title}</span>
            {item.email ? <span className="mt-0.5 block truncate text-xs font-semibold text-platforma-muted">{item.email}</span> : null}
          </span>
        </div>
        <span className={capacityClass(item.capacity_status)}>{capacityLabel(item.capacity_status, t)}</span>
      </div>
      <div className="mt-4 grid grid-cols-4 gap-2">
        <WorkloadMetric label={t("tasks.workloadOpen")} value={item.open} />
        <WorkloadMetric label={t("tasks.workloadProgress")} value={item.in_progress} />
        <WorkloadMetric label={t("tasks.workloadOverdue")} value={item.overdue} tone="red" />
        <WorkloadMetric label={t("tasks.workloadToday")} value={item.due_today} tone="amber" />
      </div>
      {item.oldest_due_at ? (
        <p className="mt-3 flex items-center gap-1.5 truncate text-xs font-semibold text-platforma-muted">
          <Clock3 size={13} />
          {t("tasks.workloadOldest")}: {formatDateTime(item.oldest_due_at)}
        </p>
      ) : null}
    </button>
  );
}

function WorkloadMetric({ label, value, tone = "slate" }: { label: string; value: number; tone?: "slate" | "red" | "amber" }) {
  const valueClass = tone === "red" ? "text-platforma-danger" : tone === "amber" ? "text-platforma-warning" : "text-platforma-text";
  return (
    <span className="rounded-control bg-platforma-card px-2 py-2 text-center ring-1 ring-platforma-border">
      <span className={`block text-base font-bold ${valueClass}`}>{value}</span>
      <span className="mt-0.5 block truncate text-[10px] font-bold uppercase text-platforma-muted">{label}</span>
    </span>
  );
}

function WorkloadTotal({ label, value, tone }: { label: string; value: number; tone: "red" | "amber" | "brand" }) {
  const Icon = tone === "red" ? AlertTriangle : tone === "amber" ? Clock3 : CheckCircle2;
  const toneClass = tone === "red" ? "bg-[var(--platforma-danger-soft)] text-platforma-danger" : tone === "amber" ? "bg-[var(--platforma-warning-soft)] text-platforma-warning" : "bg-brand-50 text-brand-700";
  return (
    <span className={`inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-bold ${toneClass}`}>
      <Icon size={14} />
      {label}: {value}
    </span>
  );
}

function capacityLabel(status: string, t: (key: string) => string) {
  const key = `tasks.workloadStatus.${status}`;
  const value = t(key);
  return value === key ? status : value;
}

function capacityClass(status: string) {
  if (status === "overloaded") return "shrink-0 rounded-full bg-[var(--platforma-danger-soft)] px-2 py-1 text-[10px] font-bold uppercase text-platforma-danger ring-1 ring-platforma-danger/20";
  if (status === "busy") return "shrink-0 rounded-full bg-[var(--platforma-warning-soft)] px-2 py-1 text-[10px] font-bold uppercase text-platforma-warning ring-1 ring-platforma-warning/[0.24]";
  if (status === "idle") return "shrink-0 rounded-full bg-surface-muted px-2 py-1 text-[10px] font-bold uppercase text-platforma-muted ring-1 ring-platforma-border";
  return "shrink-0 rounded-full bg-[var(--platforma-success-soft)] px-2 py-1 text-[10px] font-bold uppercase text-platforma-success ring-1 ring-platforma-success/[0.18]";
}
