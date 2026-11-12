import type { Task } from "../types";

type Translate = (key: string, vars?: Record<string, string | number>) => string;

export function taskTitle(task: Task, t: Translate) {
  const copy = task.system_copy;
  return copy?.title ? t(`taskWorkspace.followUp.${copy.status}.title`, { id: task.appointment ?? "" }) : task.title;
}

export function taskDescription(task: Task, t: Translate) {
  const copy = task.system_copy;
  if (!copy?.description) return task.description;
  const description = t(`taskWorkspace.followUp.${copy.status}.description`);
  return copy.reason && copy.status !== "completed" ? `${description}\n${t("taskWorkspace.followUp.reason", { reason: copy.reason })}` : description;
}
