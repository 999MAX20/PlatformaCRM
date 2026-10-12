import type { Task } from "../../types";
import { dateInTimeZone, minutesInTimeZone } from "../../lib/format.ts";

export function taskDateInput(value: string | null | undefined, zone: string) {
  if (!value) return "";
  const minutes = minutesInTimeZone(value, zone);
  return `${dateInTimeZone(value, zone)}T${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

// datetime-local is a business wall time, independent of the browser's zone.
export function taskDateISO(value: string, zone: string): string | null {
  if (!value) return null;
  const wall = Date.parse(`${value}:00Z`);
  let instant = wall;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const shown = Date.parse(`${taskDateInput(new Date(instant).toISOString(), zone)}:00Z`);
    instant += wall - shown;
  }
  if (taskDateInput(new Date(instant).toISOString(), zone) !== value) throw new Error("Invalid local time");
  return new Date(instant).toISOString();
}

export function taskGroup(task: Task, zone: string, now = new Date()) {
  if (task.status === "done" || task.status === "cancelled") return task.status;
  if (!task.due_at) return "noDue";
  if (new Date(task.due_at) < now) return "overdue";
  return dateInTimeZone(task.due_at, zone) === dateInTimeZone(now, zone) ? "today" : "later";
}

export function taskDateLabel(value: string | null | undefined, zone: string, language: string) {
  return value ? new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language, {
    timeZone: zone, year: "numeric", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(value)) : "—";
}
