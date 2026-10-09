import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "../../api/notifications";
import { Card } from "../../components/ui/Card";
import { Switch } from "../../components/ui/Switch";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import type { Notification, NotificationPreference } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { SettingsFeedback } from "../settings/components/SettingsLayout";
import { SettingsQueryState } from "../settings/components/SettingsQueryState";
import { notificationCategories } from "../settings/settingsConfig";

export function NotificationPreferencesCard() {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  return <PersonalPreferences key={`${business?.id}:${user?.id}`} />;
}

function PersonalPreferences() {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const cache = useQueryClient();
  const canView = hasPermission(user, business?.id, "notifications", "view");
  const canUpdate = hasPermission(user, business?.id, "notifications", "update");
  const preferences = useQuery({
    queryKey: ["notification-preferences", business?.id, user?.id],
    queryFn: () => notificationsApi.preferences.listAll({ business: business!.id, user: "me" }),
    enabled: Boolean(business && user && canView),
  });
  const save = useMutation({
    mutationFn: ({ category, enabled }: { category: Notification["category"]; enabled: boolean }) => {
      if (!business || !user || !canUpdate) throw new Error(t("account.businessRequired"));
      const existing = preferences.data?.find(item => item.category === category);
      const payload: Partial<NotificationPreference> = { business: business.id, user: user.id, category, in_app_enabled: enabled };
      return existing ? notificationsApi.preferences.update({ id: existing.id, payload }) : notificationsApi.preferences.create(payload);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["notification-preferences"] });
      void cache.invalidateQueries({ queryKey: ["notifications"] });
      void cache.invalidateQueries({ queryKey: ["notifications-summary"] });
    },
  });
  return <Card id="notifications" padding="md" className="scroll-mt-36 lg:scroll-mt-24">
    <h2 className="mb-2 text-base font-bold">{t("account.notificationsEyebrow")}</h2>
    <p className="mb-4 text-sm leading-6 text-platforma-subtle">{t("settings.workflow.personalNotifications", { business: business?.name || "—" })}</p>
    {!business ? <p className="text-sm">{t("account.notificationsNoBusiness")}</p> : !canView ? <p className="text-sm">{t("settings.workflow.notificationsForbidden")}</p> : <>
      <SettingsQueryState queries={[preferences]} />
      {preferences.isSuccess && <div className="divide-y divide-platforma-border">
        {notificationCategories.map(item => {
          const enabled = preferences.data.find(preference => preference.category === item.category)?.in_app_enabled !== false;
          const current = save.variables?.category === item.category;
          return <div key={item.category} className="py-3">
            <div className="flex min-h-11 items-center justify-between gap-4">
              <label htmlFor={`account-notification-${item.category}`} className="min-w-0 cursor-pointer">
                <span className="block text-sm font-semibold">{t(item.titleKey)}</span>
                <span className="mt-1 block text-xs leading-5 text-platforma-subtle">{t(item.descriptionKey)}</span>
              </label>
              <Switch id={`account-notification-${item.category}`} label={t(item.titleKey)} checked={enabled}
                disabled={!canUpdate || save.isPending || preferences.isFetching} isLoading={current && save.isPending}
                onChange={value => save.mutate({ category: item.category, enabled: value })} />
            </div>
            {current && <div className="mt-2"><SettingsFeedback error={save.error} saved={save.isSuccess} /></div>}
          </div>;
        })}
      </div>}
    </>}
  </Card>;
}
