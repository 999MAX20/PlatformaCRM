import { Switch } from "../../../components/ui/Switch";
import { SettingsFeedback, SettingsSection } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { notificationCategories } from "../settingsConfig";
import type { SettingsModel } from "../useSettingsModel";

export function NotificationPreferencesSection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, business, notificationPreferences, notificationPreferenceMutation, preferenceByCategory, canUpdateNotifications } = model;
  return <SettingsSection id="notification-preferences" active={activeSettingsSection} title={t("settings.section.notification-preferences")}>
    <div className="p-4 sm:p-5">
      <p className="mb-4 max-w-3xl text-sm leading-6 text-platforma-subtle">{t("settings.notificationsText")}</p>
      <SettingsQueryState queries={[notificationPreferences]} />
      {!business?.id ? <p className="text-sm text-platforma-subtle">{t("account.notificationsNoBusiness")}</p> : notificationPreferences.isSuccess && <div className="divide-y divide-platforma-border">
        {notificationCategories.map(item => {
          const enabled = preferenceByCategory.get(item.category)?.in_app_enabled !== false;
          const current = notificationPreferenceMutation.variables?.category === item.category;
          return <div key={item.category} className="py-4">
            <div className="flex min-h-11 items-center justify-between gap-4">
              <label htmlFor={"settings-notification-" + item.category} className="min-w-0 cursor-pointer">
                <span className="block text-sm font-semibold">{t(item.titleKey)}</span>
                <span className="mt-1 block text-sm leading-5 text-platforma-subtle">{t(item.descriptionKey)}</span>
              </label>
              <div className="flex min-h-11 shrink-0 items-center gap-3">
                <span className="hidden text-xs text-platforma-subtle sm:inline">{t(enabled ? "settings.enabled" : "settings.disabled")}</span>
                <Switch id={"settings-notification-" + item.category} checked={enabled} label={t(item.titleKey)}
                  disabled={!canUpdateNotifications || notificationPreferenceMutation.isPending}
                  isLoading={current && notificationPreferenceMutation.isPending}
                  onChange={value => notificationPreferenceMutation.mutate({ category: item.category, enabled: value })} />
              </div>
            </div>
            {current && <div className="mt-2"><SettingsFeedback error={notificationPreferenceMutation.error} saved={notificationPreferenceMutation.isSuccess} /></div>}
          </div>;
        })}
      </div>}
    </div>
  </SettingsSection>;
}
