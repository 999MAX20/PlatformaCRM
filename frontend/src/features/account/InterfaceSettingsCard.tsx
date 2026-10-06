import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { updateCurrentUser } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { assertCurrentSession } from "../../api/token";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import { ErrorState } from "../../components/ui/StateViews";
import { prepareLanguage, useI18n, type Language } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { availableStartPages } from "../../lib/startPage";
import { tokenStorage } from "../../lib/storage";
import type { UserPreference } from "../../types";
import { NotificationSoundControl } from "./NotificationSoundControl";

export function InterfaceSettingsCard() {
  const { user, refreshUser } = useAuth();
  const { business } = useActiveBusiness();
  const { t, language, setLanguage } = useI18n();
  const pages = availableStartPages(user, business?.id);
  const savedStartPage = pages.find(({ value }) => value === user?.preferences?.start_page)?.value || "dashboard";
  const [selectedStartPage, setSelectedStartPage] = useState<UserPreference["start_page"]>(savedStartPage);
  useEffect(() => setSelectedStartPage(savedStartPage), [user?.id, business?.id, savedStartPage]);
  const savedLanguage = user?.preferences?.language || language;
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(savedLanguage);
  useEffect(() => setSelectedLanguage(savedLanguage), [user?.id, savedLanguage]);
  useEffect(() => {
    if (user?.preferences?.language) setLanguage(user.preferences.language);
  }, [user?.preferences?.language, setLanguage]);
  const mutation = useMutation({
    mutationFn: async (value: Pick<UserPreference, "language" | "start_page">) => {
      const generation = tokenStorage.getGeneration();
      await prepareLanguage(value.language);
      assertCurrentSession(generation);
      const updated = await updateCurrentUser({ preferences: value });
      return { updated, generation };
    },
    onSuccess: async ({ updated, generation }, value) => {
      assertCurrentSession(generation);
      await refreshUser();
      assertCurrentSession(generation);
      setLanguage(updated.preferences?.language || value.language);
    },
  });

  return (
    <Card id="interface" padding="md" className="scroll-mt-36 lg:scroll-mt-24">
      <h2 className="mb-3 text-base font-bold">{t("account.interfaceTitle")}</h2>
      {mutation.error ? <ErrorState error={mutation.error} message={getApiErrorMessage(mutation.error)} /> : null}
      {mutation.isSuccess ? <p role="status" className="mb-3 text-sm text-platforma-success">{t("account.interfaceSaved")}</p> : null}
      <form className="grid max-w-[560px] gap-3 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); mutation.mutate({ language: selectedLanguage, start_page: selectedStartPage }); }}>
        <div className="min-w-0 flex-1">
          <Select label={t("common.language")} value={selectedLanguage} disabled={mutation.isPending}
            onChange={(event) => { mutation.reset(); setSelectedLanguage(event.target.value as Language); }}
            options={[{ value: "ru", label: "Русский" }, { value: "kk", label: "Қазақша" }, { value: "en", label: "English" }]} />
        </div>
        <Select label={t("account.startPage")} value={selectedStartPage} disabled={mutation.isPending}
          onChange={(event) => { mutation.reset(); setSelectedStartPage(event.target.value as UserPreference["start_page"]); }}
          options={pages.map(({ value, label }) => ({ value, label: t(label) }))} />
        <div className="flex sm:col-span-2 sm:justify-end">
          <Button size="sm" type="submit" disabled={selectedLanguage === savedLanguage && selectedStartPage === savedStartPage} isLoading={mutation.isPending}>{t("common.save")}</Button>
        </div>
      </form>
      <NotificationSoundControl />
    </Card>
  );
}
