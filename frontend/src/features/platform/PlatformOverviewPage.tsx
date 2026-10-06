import { useQuery } from "@tanstack/react-query";
import { Bot, Building2, CircleAlert, CreditCard, MessageCircle, ShieldAlert, Sparkles, Store, TrendingUp, Users } from "lucide-react";
import { Link } from "react-router";

import { platformApi } from "../../api/platform";
import { Card, CardBody } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";

const metricCards = [
  { key: "total_businesses", labelKey: "platform.overview.totalMerchants", icon: Store, tone: "bg-[var(--platforma-info-soft)] text-platforma-info" },
  { key: "active_businesses", labelKey: "platform.overview.activeMerchants", icon: Building2, tone: "bg-[var(--platforma-success-soft)] text-platforma-success" },
  { key: "trial_businesses", labelKey: "platform.overview.trialMerchants", icon: Sparkles, tone: "bg-discovery-50 text-discovery-700" },
  { key: "active_subscriptions", labelKey: "platform.overview.activeSubscriptions", icon: CreditCard, tone: "bg-[var(--platforma-info-soft)] text-platforma-info" },
  { key: "total_users", labelKey: "platform.overview.users", icon: Users, tone: "bg-surface-muted text-platforma-subtle" },
  { key: "bot_count", labelKey: "platform.overview.bots", icon: Bot, tone: "bg-brand-50 text-brand-700" },
] as const;

function formatMoney(value: string, language: "ru" | "kk" | "en") {
  const locale = language === "en" ? "en-US" : language === "kk" ? "kk-KZ" : "ru-KZ";
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(value || 0));
}

export function PlatformOverviewPage() {
  const { t, language } = useI18n();
  const overview = useQuery({ queryKey: ["platform-overview"], queryFn: platformApi.overview });

  if (overview.isLoading) return <LoadingState scope="page" />;
  if (overview.isError || !overview.data) return <ErrorState message={t("platform.overview.error")} />;

  const data = overview.data;

  return (
    <div className="space-y-5" data-testid="platform-overview-ready">
      <section className="glass-panel rounded-[2rem] p-6 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">{t("platform.overview.eyebrow")}</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-midnight sm:text-5xl">{t("platform.overview.title")}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-platforma-subtle">
              {t("platform.overview.description")}
            </p>
          </div>
          <Link to="/platform/merchants">
            <Button variant="secondary" className="rounded-full">
              <Store size={17} />
              {t("platform.nav.merchants")}
            </Button>
          </Link>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          const value = data[metric.key];
          return (
            <Card key={metric.key}>
              <CardBody className="flex items-center justify-between gap-4 p-5">
                <div>
                  <p className="text-sm font-semibold text-platforma-faint">{t(metric.labelKey)}</p>
                  <p className="mt-2 text-3xl font-bold tracking-tight text-midnight">{value}</p>
                </div>
                <div className={`grid h-12 w-12 place-items-center rounded-2xl ${metric.tone}`}>
                  <Icon size={22} />
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardBody className="p-5">
            <ShieldAlert className="text-platforma-warning" size={22} />
            <p className="mt-4 text-3xl font-bold text-midnight">{data.operations_summary.attention_merchants}</p>
            <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.attentionMerchants")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <CircleAlert className="text-platforma-danger" size={22} />
            <p className="mt-4 text-3xl font-bold text-midnight">{data.operations_summary.form_errors_30d}</p>
            <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.formErrors")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <MessageCircle className="text-brand-600" size={22} />
            <p className="mt-4 text-3xl font-bold text-midnight">{data.operations_summary.handoff_conversations}</p>
            <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.handoffConversations")}</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="p-5">
            <TrendingUp className="text-platforma-success" size={22} />
            <p className="mt-4 text-3xl font-bold text-midnight">{data.operations_summary.new_leads_30d}</p>
            <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.newLeads")}</p>
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardBody className="p-6">
            <p className="text-sm font-semibold text-platforma-faint">{t("platform.overview.mrr")}</p>
            <p className="mt-3 text-5xl font-bold tracking-tight text-midnight">{formatMoney(data.mrr_estimate, language)} ₸</p>
            <p className="mt-3 text-sm leading-6 text-platforma-faint">
              {t("platform.overview.mrrText")}
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-3xl border border-platforma-border bg-surface-muted p-4">
                <MessageCircle className="text-brand-600" size={22} />
                <p className="mt-4 text-2xl font-bold text-midnight">{data.conversations_30d}</p>
                <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.conversations")}</p>
              </div>
              <div className="rounded-3xl border border-platforma-border bg-surface-muted p-4">
                <Sparkles className="text-platforma-info" size={22} />
                <p className="mt-4 text-2xl font-bold text-midnight">{data.ai_requests_30d}</p>
                <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.aiRequests")}</p>
              </div>
              <div className="rounded-3xl border border-platforma-border bg-surface-muted p-4">
                <Bot className="text-platforma-info" size={22} />
                <p className="mt-4 text-2xl font-bold text-midnight">{data.active_bot_channels}</p>
                <p className="mt-1 text-sm font-semibold text-platforma-faint">{t("platform.overview.activeChannels")}</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardBody className="flex flex-col gap-3 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[var(--platforma-success-soft)] text-platforma-success">
              <CircleAlert size={21} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-midnight">{t("platform.overview.errorsTitle")}</h2>
              <p className="mt-1 text-sm leading-6 text-platforma-faint">
                {t("platform.overview.errorsText", {
                  errors: data.errors.count,
                  connectors: data.operations_summary.failed_connectors,
                  merchants: data.operations_summary.no_sales_data_merchants,
                })}
              </p>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
