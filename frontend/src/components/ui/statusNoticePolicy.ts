import type { AppError } from "../../api/appError";

export type StatusNoticeTone = "success" | "info" | "warning" | "danger";

export function appErrorNoticeTone(error: AppError): StatusNoticeTone {
  if (error.category === "not_found") return "info";
  if (["authentication", "permission", "conflict", "rate_limit", "offline", "provider"].includes(error.category)) {
    return "warning";
  }
  return "danger";
}
