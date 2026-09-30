import { useState } from "react";
import { Volume2 } from "lucide-react";

import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { playNotificationSound, setNotificationSoundPreference, unlockNotificationSound, useNotificationSoundPreference } from "../../lib/notificationSound";
import { useAuth } from "../auth/AuthProvider";

export function NotificationSoundControl() {
  const { user } = useAuth();
  const { t } = useI18n();
  const enabled = useNotificationSoundPreference(user?.id);
  const [error, setError] = useState(false);

  return (
    <div className="mt-4 border-t border-platforma-border pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{t("account.notificationSound")}</p>
          <p className="mt-1 text-xs text-platforma-subtle">{t("account.soundThisBrowser")}</p>
        </div>
        <div className="flex items-center gap-3">
          <Button size="sm" variant="secondary" onClick={async () => {
            setError(false);
            try { if (!await unlockNotificationSound() || !playNotificationSound()) setError(true); }
            catch { setError(true); }
          }}><Volume2 size={16} />{t("account.previewSound")}</Button>
          <button type="button" role="switch" aria-label={t("account.notificationSound")} aria-checked={enabled}
            className="platforma-focus-ring flex w-12 shrink-0 items-center justify-center rounded-control"
            onClick={async () => {
              if (!user) return;
              setError(false);
              try {
                if (!enabled && !await unlockNotificationSound()) { setError(true); return; }
                setNotificationSoundPreference(user.id, !enabled);
              } catch { setError(true); }
            }}>
            <span aria-hidden="true" className={`flex h-5 w-9 items-center rounded-full px-0.5 transition-colors ${enabled ? "bg-brand-500" : "bg-slate-300"}`}><span className={`h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${enabled ? "translate-x-4" : "translate-x-0"}`} /></span>
          </button>
        </div>
      </div>
      {error ? <div className="mt-3"><ErrorState message={t("account.soundUnavailable")} /></div> : null}
    </div>
  );
}
