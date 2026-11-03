export const recordWorkflows = ["planned", "completed", "cancelled", "no_show"] as const;

export function savedRecordPeriod(value: string | null) {
  const params = new URLSearchParams(value || "");
  const from = params.get("from") || "";
  const to = params.get("to") || from;
  const valid = (day: string) => {
    const date = new Date(`${day}T00:00:00Z`);
    return /^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === day;
  };
  return valid(from) && valid(to) && from <= to ? new URLSearchParams({ from, to }) : null;
}

export const recordAdvancedKeys = ["resource", "responsible_user", "confirmed", "branch"] as const;
const recordFilterKeys = ["search", "from", "to", "workflow", "attention", "client", ...recordAdvancedKeys, "ordering", "page"];

export function patchRecordFilters(current: URLSearchParams, patch: Record<string, string>) {
  const next = new URLSearchParams(current);
  Object.entries(patch).forEach(([key, value]) => { if (value) next.set(key, value); else next.delete(key); });
  next.delete("page");
  return next;
}

export function resetRecordFilters(current: URLSearchParams, today?: string) {
  const next = new URLSearchParams(current);
  recordFilterKeys.forEach(key => next.delete(key));
  if (today) { next.set("from", today); next.set("to", today); }
  return next;
}

export function nextRecordDay(day: string) {
  const value = new Date(`${day}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(value.getTime()) || value.toISOString().slice(0, 10) !== day) return day;
  value.setUTCDate(value.getUTCDate() + 1);
  return value.toISOString().slice(0, 10);
}

export function recordWorkspaceParams(params: URLSearchParams, today: string, business: number) {
  const attention = params.get("attention") || undefined;
  const client = params.get("client") || undefined;
  const from = params.get("from") || (attention || client ? undefined : today);
  const to = params.get("to") || from;
  return {
    business, attention, client, start_from: from, start_to: to ? nextRecordDay(to) : undefined,
    q: params.get("search") || undefined,
    workflow: params.get("workflow") || undefined,
    confirmed: params.get("confirmed") || undefined,
    branch: params.get("branch") || undefined,
    resource: params.get("resource") || undefined,
    responsible_user: params.get("responsible_user") || undefined,
    ordering: params.get("ordering") || "start_at",
    page: params.get("page") || "1", page_size: params.get("page_size") || "20",
  };
}

export function recordReturnPath(value: unknown) {
  return typeof value === "string" && !/[\r\n\t]/.test(value) &&
    (value === "/app/appointments" || value.startsWith("/app/appointments?"))
    ? value : "/app/appointments";
}
