import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "./AuthProvider";

export function BusinessAccessRevoked() {
  const { t } = useI18n();
  const { logout } = useAuth();
  return <main className="flex min-h-dvh items-center justify-center bg-surface p-4 text-ink sm:p-6">
    <section className="w-full max-w-lg space-y-6 rounded-card border border-platforma-border bg-surface-card p-6 sm:p-8" aria-labelledby="business-access-revoked">
      <h1 id="business-access-revoked" className="text-xl font-semibold">{t("teamAccess.revoked")}</h1>
      <Button type="button" variant="secondary" size="lg" onClick={logout}>{t("header.logout")}</Button>
    </section>
  </main>;
}
