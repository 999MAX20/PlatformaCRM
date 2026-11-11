import { useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { businessesApi } from "../../api/businesses";
import { BusinessSettingsForm } from "../../components/forms/BusinessSettingsForm";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import type { Business } from "../../types";
import { useAuth } from "../auth/AuthProvider";
import { BusinessWorkspaceNav } from "./components/BusinessWorkspaceNav";

export function CompanyPage() {
  const { t } = useI18n();
  const { user } = useAuth();
  const query = useActiveBusiness();
  const cache = useQueryClient();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("nav.business") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const mutation = useMutation({
    mutationFn: (payload: Partial<Business>) => businessesApi.update({ id: query.business!.id, payload }),
    onSuccess: async () => {
      await Promise.all(["businesses", "branches", "branch-catalog", "branch-configuration"].map(key => cache.invalidateQueries({ queryKey: [key] })));
    },
  });
  return <div className="space-y-4">
    <BusinessWorkspaceNav />
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} /> : query.business ?
      <section className="mx-auto max-w-3xl rounded-card border border-platforma-border bg-surface-card">
        <h2 className="border-b border-platforma-border px-5 py-4 text-base font-semibold">{t("business.company")}</h2>
        <BusinessSettingsForm key={query.business.id} initial={query.business} protectDraft
          readOnly={!hasPermission(user, query.business.id, "settings", "update")}
          onSubmit={payload => mutation.mutateAsync(payload)} />
      </section> : null}
  </div>;
}
