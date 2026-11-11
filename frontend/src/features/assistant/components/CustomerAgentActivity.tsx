import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { inboxApi } from "../../../api/inbox";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { hasPermission } from "../../../lib/permissions";
import type { Bot } from "../../../types";
import { useAuth } from "../../auth/AuthProvider";

export function CustomerAgentActivity({ bot }: { bot: Bot }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const allowed = hasPermission(user, bot.business, "conversations", "view");
  const summary = useQuery({ queryKey: ["agent-inbox-summary", bot.business, bot.id],
    queryFn: () => inboxApi.getAgentSummary(bot.id), enabled: allowed });
  if (!allowed) return null;
  return <section className="space-y-3 border-b border-platforma-border pb-4" data-testid="agent-activity">
    <h3 className="text-base font-semibold text-platforma-ink">{t("aiAgents.activity.title")}</h3>
    {summary.isLoading ? <LoadingState /> : summary.error ? <ErrorState error={summary.error}
      action={<Button variant="secondary" onClick={() => void summary.refetch()}>{t("common.retry")}</Button>} />
      : summary.data && <>
        <dl className="flex flex-wrap gap-x-6 gap-y-3">
          {(["total", "unread", "handoff_required"] as const).map(key => <div key={key}>
            <dt className="text-sm text-platforma-subtle">{t(`aiAgents.activity.${key}`)}</dt>
            <dd><Link className="platforma-focus-ring text-lg font-semibold underline" to={`/app/conversations?bot=${bot.id}&preset=all${key === "total" ? "" : `&status=open&${key}=true`}`}
              aria-label={`${t(`aiAgents.activity.${key}`)}: ${summary.data[key]}`}>{summary.data[key]}</Link></dd>
          </div>)}
        </dl>
        {summary.data.total === 0 && <p className="text-sm text-platforma-subtle">{t("aiAgents.activity.empty")}</p>}
      </>}
  </section>;
}
