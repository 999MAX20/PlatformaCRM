import { normalizeAppError } from "../../api/appError.ts";

type Translate = (key: string, vars?: Record<string, string | number>) => string;

/** Provider replies can still contain legacy reasons; never render their raw text. */
export function merchantSafeIntegrationError(error: unknown, t: Translate, canManage?: boolean) {
  const guidance = (cause: string) => t(`integrations.error.${cause}${canManage === true ? "Manage" : canManage === false ? "ReadOnly" : ""}`);
  if (typeof error !== "string") {
    const normalized = normalizeAppError(error);
    // HTTP authorization describes the CRM request, not a provider's token.
    if (normalized.category === "permission") return t("integrations.error.permission");
    return t(normalized.messageKey);
  }
  const reason = error.trim().toLowerCase();
  if (/^(telegram|instagram|whatsapp) integration is disabled\.?$/.test(reason)
      || reason === "integration_disabled") return t("integrations.error.integrationDisabled");
  if (reason === "the external provider could not complete the request." || reason === "provider_unavailable") return t("integrations.error.providerUnavailable");
  if (/(token|api key|access key|credential).*(missing|not configured)/.test(reason)) return guidance("credentialsMissing");
  if (/(expired|invalid|unauthorized|401)/.test(reason) && /(token|credential|key|unauthorized|401)/.test(reason)) return guidance("credentialsInvalid");
  if (/(webhook|callback).*(missing|not configured|https|invalid|weak|unsafe)/.test(reason)) return guidance("webhookRequired");
  if (/(rate limit|throttl|429|too many requests)/.test(reason)) return t("integrations.error.rateLimit");
  if (/(network|timeout|timed out|unavailable|connection refused)/.test(reason)) return t("integrations.error.providerUnavailable");
  // A provider-side 403 does not establish the current user's CRM permissions.
  if (/(forbidden|permission|403)/.test(reason)) return t("integrations.error.providerPermission");
  if (/(not configured|configuration|environment|client id|app id)/.test(reason)) return t("integrations.error.supportReview");
  return t("integrations.error.actionRequired");
}
