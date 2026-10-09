import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, LogOut } from "lucide-react";
import { useEffect, useState } from "react";

import { changePassword, getCurrentUserLoginHistory, getMfaStatus, updateCurrentUser } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { formatDateTime } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { SecuritySettingRow } from "./SecuritySettingRow";
import { ActiveSessions } from "./ActiveSessions";
import { AvatarEditor } from "./AvatarEditor";
import { EmailSecurityRow } from "./EmailSecurityRow";
import { MfaSecurityCard } from "./MfaSecurityCard";
import { AccountSectionNav } from "./AccountSectionNav";
import { InterfaceSettingsCard } from "./InterfaceSettingsCard";
import { AccountAccessSummary } from "./AccountAccessSummary";
import { DocumentLinks } from "../documents/DocumentLinks";
import { NotificationPreferencesCard } from "./NotificationPreferencesCard";
import "./accountPage.css";

export function AccountPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const { user, refreshUser, logout } = useAuth();
  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || "",
    phone: user?.phone || "",
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
    mfa_code: "",
  });
  const profileDirty = profileForm.full_name !== (user?.full_name || "") || profileForm.phone !== (user?.phone || "");
  const [profileSaved, setProfileSaved] = useState(false);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  const loginHistory = useQuery({
    queryKey: ["account-login-history", user?.id],
    queryFn: getCurrentUserLoginHistory,
    enabled: Boolean(user?.id),
  });
  const mfaStatus = useQuery({ queryKey: ["mfa-status"], queryFn: getMfaStatus, enabled: Boolean(user?.id) });

  useEffect(() => {
    setProfileForm({
      full_name: user?.full_name || "",
      phone: user?.phone || "",
    });
  }, [user?.id, user?.full_name, user?.phone]);
  const profileMutation = useMutation({
    mutationFn: () => updateCurrentUser(profileForm),
    onSuccess: async () => {
      setProfileSaved(true);
      await refreshUser();
      window.setTimeout(() => setProfileSaved(false), 2600);
    },
  });
  const passwordMutation = useMutation({
    mutationFn: () => {
      if (passwordForm.new_password !== passwordForm.confirm_password) {
        throw new Error(t("account.passwordMismatch"));
      }
      return changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
        mfa_code: passwordForm.mfa_code || undefined,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["account-sessions"] });
      setPasswordSaved(true);
      setPasswordModalOpen(false);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "", mfa_code: "" });
      window.setTimeout(() => setPasswordSaved(false), 2600);
    },
  });
  return (
    <div data-account-page className="relative mx-auto max-w-[var(--account-content-width)] [&_input]:min-h-11 sm:[&_input]:min-h-10 [&_button]:min-h-11 sm:[&_button]:min-h-9">
      <AccountSectionNav />
      <div className="min-w-0 space-y-4">
      <Card id="profile" padding="md" className="scroll-mt-36 lg:scroll-mt-24">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-platforma-text">{t("account.profileEyebrow")}</h1>
          </div>
          <Button size="sm" variant="ghost" data-testid="merchant-logout" onClick={logout}><LogOut size={16} />{t("header.logout")}</Button>
        </div>
        {profileMutation.error ? <ErrorState error={profileMutation.error} message={getApiErrorMessage(profileMutation.error)} /> : null}
        {profileSaved ? <p role="status" className="mb-3 text-sm text-platforma-success">{t("account.saved")}</p> : null}
        <div className="grid gap-5 sm:grid-cols-[160px_minmax(0,1fr)]">
          <AvatarEditor user={user} />
        <form className="grid max-w-[560px] gap-3 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" onSubmit={(event) => { event.preventDefault(); profileMutation.mutate(); }}>
          <Input label={t("account.fullName")} autoComplete="name" value={profileForm.full_name} disabled={profileMutation.isPending} onChange={(event) => setProfileForm((current) => ({ ...current, full_name: event.target.value }))} />
          <Input label={t("account.phone")} type="tel" autoComplete="tel" value={profileForm.phone} disabled={profileMutation.isPending} onChange={(event) => setProfileForm((current) => ({ ...current, phone: event.target.value }))} />
          <div className="flex items-end sm:col-span-2 sm:justify-end"><Button size="sm" type="submit" disabled={!profileDirty} isLoading={profileMutation.isPending}>{t("common.save")}</Button></div>
        </form>
        </div>
        <AccountAccessSummary />
      </Card>

      <InterfaceSettingsCard />

      <Card id="security" padding="md" className="scroll-mt-36 lg:scroll-mt-24">
        <h2 className="mb-3 text-base font-bold">{t("account.loginHistoryEyebrow")}</h2>
        {passwordSaved ? <p role="status" className="mb-3 text-sm text-platforma-success">{t("account.passwordSaved")}</p> : null}
        <div className="divide-y divide-platforma-border">
          <EmailSecurityRow />
          <SecuritySettingRow icon={<KeyRound size={18} />} title={t("account.passwordLabel")}
            action={<Button size="sm" variant="secondary" aria-label={t("account.changePassword")} onClick={() => { passwordMutation.reset(); setPasswordModalOpen(true); }}>{t("account.securityEdit")}</Button>} />
          <MfaSecurityCard />
        </div>
        <ActiveSessions />
        {user?.social_identities?.length ? <details className="border-t border-platforma-border py-3">
          <summary className="cursor-pointer text-sm font-semibold">{t("account.connectedTitle")}</summary>
          {user.social_identities.map((identity) => <p key={`${identity.provider}-${identity.email}`} className="mt-2 break-all text-sm">{identity.provider} · {identity.email} · {identity.email_verified ? t("account.verified") : t("account.notVerified")}</p>)}
        </details> : null}
        <details className="border-t border-platforma-border pt-3">
          <summary className="cursor-pointer text-sm font-semibold">{t("account.loginHistoryTitle")}</summary>
          {loginHistory.isLoading ? <LoadingState /> : loginHistory.error ? <ErrorState error={loginHistory.error} message={getApiErrorMessage(loginHistory.error)} action={<Button size="sm" variant="secondary" onClick={() => void loginHistory.refetch()}>{t("common.retry")}</Button>} /> : <div className="mt-2 divide-y divide-platforma-border">
            {(loginHistory.data || []).slice(0, 5).map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
              <span>{formatDateTime(item.created_at)}</span><span className="text-platforma-subtle" title={item.user_agent || t("account.noDevice")}>{item.ip_address || t("account.noIp")}</span><span>{t(`status.${item.status}`)}</span>
            </div>)}
            {!loginHistory.data?.length ? <p className="text-sm text-platforma-subtle">{t("account.noLoginHistory")}</p> : null}
          </div>}
        </details>
      </Card>

      <NotificationPreferencesCard />

      <DocumentLinks />
      <Modal
        title={t("account.changePassword")}
        open={passwordModalOpen}
        onClose={() => {
          if (passwordMutation.isPending) return;
          setPasswordModalOpen(false);
          setPasswordForm({ current_password: "", new_password: "", confirm_password: "", mfa_code: "" });
        }}
      >
        <div className="rounded-3xl bg-white p-4 sm:p-5">
          <div className="mb-4 flex items-start gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-700">
              <KeyRound size={21} />
            </div>
            <div>
              <p className="text-sm font-black text-midnight">{t("account.securityTitle")}</p>
              <p className="mt-1 text-sm font-semibold leading-6 text-platforma-faint">{t("account.securityText")}</p>
            </div>
          </div>
          {passwordMutation.error ? <div className="mb-4"><ErrorState error={passwordMutation.error} message={getApiErrorMessage(passwordMutation.error)} /></div> : null}
          <form
            className="grid gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              passwordMutation.mutate();
            }}
          >
            <Input label={t("account.currentPassword")} type="password" value={passwordForm.current_password} onChange={(event) => setPasswordForm((current) => ({ ...current, current_password: event.target.value }))} required />
            <Input label={t("account.newPassword")} type="password" value={passwordForm.new_password} onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))} required />
            <Input label={t("account.confirmPassword")} type="password" value={passwordForm.confirm_password} onChange={(event) => setPasswordForm((current) => ({ ...current, confirm_password: event.target.value }))} required />
            {mfaStatus.data?.enabled ? <Input label={t("mfa.codeLabel")} value={passwordForm.mfa_code} onChange={(event) => setPasswordForm((current) => ({ ...current, mfa_code: event.target.value }))} autoComplete="one-time-code" required /> : null}
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <Button type="button" variant="secondary" disabled={passwordMutation.isPending} onClick={() => setPasswordModalOpen(false)}>
                {t("common.cancel")}
              </Button>
              <Button type="submit" isLoading={passwordMutation.isPending}>{t("account.changePassword")}</Button>
            </div>
          </form>
        </div>
      </Modal>
      </div>
    </div>
  );
}
