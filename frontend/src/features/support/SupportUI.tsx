import { useRef } from "react";
import { normalizeAppError } from "../../api/appError";
import { Badge, type BadgeVariant } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState, ForbiddenState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { SupportStatus } from "../../types/support";

export const supportStatuses: SupportStatus[] = ["new", "in_progress", "waiting_clinic", "waiting_internal", "resolved"];
const tones: Record<SupportStatus, BadgeVariant> = { new: "info", in_progress: "primary", waiting_clinic: "warning", waiting_internal: "warning", resolved: "success" };

export function SupportStatusBadge({ status }: { status: SupportStatus }) {
  const { t } = useI18n();
  return <Badge variant={tones[status]}>{t(`supportCases.status.${status}`)}</Badge>;
}

export function SupportError({ error, retry }: { error: unknown; retry?: () => void }) {
  const { t } = useI18n();
  const normalized = normalizeAppError(error);
  if (normalized.category === "permission") return <ForbiddenState error={normalized} />;
  return <ErrorState error={error} action={retry && normalized.category !== "not_found" ? <Button variant="secondary" onClick={retry}>{t("common.refresh")}</Button> : undefined} />;
}

export function retainSupportData(error: unknown) {
  return ["offline", "temporary", "provider", "rate_limit", "internal"].includes(normalizeAppError(error).category);
}

export function supportDate(value: string | null, language: string, timeZone: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-RU" : "en-GB", {
    dateStyle: "medium", timeStyle: "short", timeZone,
  }).format(new Date(value));
}

export function useSupportKey() {
  const current = useRef<{ payload: string; key: string } | null>(null);
  return {
    forPayload(payload: unknown) {
      const serialized = JSON.stringify(payload);
      if (!current.current || current.current.payload !== serialized) current.current = { payload: serialized, key: crypto.randomUUID() };
      return current.current.key;
    },
    reset() { current.current = null; },
  };
}
