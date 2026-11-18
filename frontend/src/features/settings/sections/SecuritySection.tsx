import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { SettingsSection, SettingsTabs } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { auditEventTitle, loginStatusLabel, riskClass, riskLabel } from "../settingsUtils";
import type { SettingsModel } from "../useSettingsModel";

export function SecuritySection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, auditLogs, loginHistory, supportGrants, locale, business, securityFilters, setSecurityFilters } = model;
  const [tab, setTab] = useState<"audit" | "logins" | "support">("audit");
  const date = (value: string) => new Date(value).toLocaleString(locale, { timeZone: business?.timezone || undefined });
  const { failedOnly } = securityFilters;
  const logins = loginHistory.data?.results || [];
  const history = tab === "audit" ? auditLogs : loginHistory;
  const page = tab === "audit" ? securityFilters.auditPage : securityFilters.loginPage;
  return <SettingsSection id="security-center" active={activeSettingsSection} title={t("settings.section.security-center")}>
    <div className="space-y-4 p-4 sm:p-5">
      <p className="text-xs leading-5 text-platforma-subtle">{t("settings.workflow.securityHistoryScope")}</p>
      <SettingsTabs value={tab} onChange={setTab} label={t("settings.section.security-center")} items={[
        { value: "audit", label: t("settings.redesign.auditTab") },
        { value: "logins", label: t("settings.redesign.loginsTab") },
        { value: "support", label: t("settings.redesign.supportTab") },
      ]} />
      {tab !== "support" && <div className="max-w-xs"><Select label={t("settings.clarity.period")} value={securityFilters.period}
        options={["all", "7", "30", "90"].map(value => ({ value, label: t(`settings.clarity.period.${value}`) }))}
        onChange={event => { const period = event.target.value; setSecurityFilters(current => ({ ...current, period, date_from: period === "all" ? undefined : new Date(Date.now() - Number(period) * 86400000).toISOString(), auditPage: 1, loginPage: 1 })); }} /></div>}
      {tab === "audit" && <>
        <SettingsQueryState queries={[auditLogs]} />
        {auditLogs.isSuccess && <div className="divide-y divide-platforma-border">
          {(auditLogs.data?.results || []).map(log => <div key={log.id} className="flex items-start justify-between gap-3 py-4">
            <div className="min-w-0"><p className="text-sm font-semibold">{auditEventTitle(log.action, log.entity_type, t)} #{log.entity_id}</p><p className="mt-1 break-words text-xs text-platforma-subtle">{log.actor_email || t("settings.systemActor")} · {date(log.created_at)}</p></div>
            <span className={riskClass(log.risk_level)}>{riskLabel(log.risk_level, t)}</span>
          </div>)}
          {!auditLogs.data?.results.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noAuditEvents")}</p>}
        </div>}
      </>}
      {tab === "logins" && <>
        <label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={failedOnly} onChange={event => setSecurityFilters(current => ({ ...current, failedOnly: event.target.checked, loginPage: 1 }))} className="h-5 w-5 accent-brand-500" />{t("settings.workflow.failedOnly")}</label>
        <SettingsQueryState queries={[loginHistory]} />
        {loginHistory.isSuccess && <div className="divide-y divide-platforma-border">
          {logins.map(item => <div key={item.id} className="flex items-start justify-between gap-3 py-4">
            <div className="min-w-0"><p className="break-all text-sm font-semibold">{item.email || item.user_email}</p><p className="mt-1 text-xs text-platforma-subtle">{item.ip_address || t("settings.noIp")} · {date(item.created_at)}</p></div>
            <span className={"shrink-0 text-xs font-semibold " + (item.status === "success" ? "text-platforma-success" : "text-platforma-danger")}>{loginStatusLabel(item.status, t)}</span>
          </div>)}
          {!logins.length && <p className="py-8 text-sm text-platforma-subtle">{t(failedOnly ? "settings.workflow.noFailedLogins" : "settings.noLoginHistory")}</p>}
        </div>}
      </>}
      {tab !== "support" && history.isSuccess && history.data.count > 0 && <nav aria-label={t("pagination.navigation")} className="flex flex-wrap items-center justify-between gap-3 border-t border-platforma-border pt-3">
        <p className="text-sm text-platforma-subtle" aria-live="polite">{t("pagination.visibleRange", { from: (page - 1) * 25 + 1, to: Math.min(page * 25, history.data.count), total: history.data.count })}</p>
        <div className="flex gap-2">{[-1, 1].map(direction => <Button key={direction} type="button" variant="secondary" disabled={history.isFetching || (direction < 0 ? !history.data.previous : !history.data.next)}
          onClick={() => setSecurityFilters(current => ({ ...current, [tab === "audit" ? "auditPage" : "loginPage"]: page + direction }))}>{t(direction < 0 ? "pagination.previous" : "pagination.next")}</Button>)}</div>
      </nav>}
      {tab === "support" && <>
        <SettingsQueryState queries={[supportGrants]} />
        {supportGrants.isSuccess && <div className="divide-y divide-platforma-border">
          {(supportGrants.data || []).map(grant => <div key={grant.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
            <div><p className="break-all text-sm font-semibold">{grant.user_email}</p><p className="mt-1 text-xs text-platforma-subtle">{t("settings.until")} {date(grant.expires_at)}</p></div>
            <span className="text-xs text-platforma-subtle">{t(grant.is_active ? new Date(grant.expires_at).getTime() > Date.now() ? "settings.active" : "settings.expired" : "settings.inactive")}</span>
          </div>)}
          {!supportGrants.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noSupportGrants")}</p>}
        </div>}
      </>}
    </div>
  </SettingsSection>;
}
