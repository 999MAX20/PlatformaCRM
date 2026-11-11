import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { branchesApi, type Branch, type BranchConfiguration } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Service } from "../../../types";

export function ServiceBranchTerms({ branch, service, config, disabled, onDirtyChange }: {
  branch: Branch; service: Service; config: BranchConfiguration; disabled: boolean; onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const offer = config.offers.find(item => item.service === service.id);
  const [duration, setDuration] = useState(String(offer?.duration_minutes ?? service.duration_minutes));
  const [price, setPrice] = useState(String(offer ? offer.price_from ?? "" : service.price_from ?? ""));
  const [active, setActive] = useState(offer?.is_active ?? false);
  const [saved, setSaved] = useState(JSON.stringify([duration, price, active]));
  const dirty = saved !== JSON.stringify([duration, price, active]);
  const mutation = useMutation({ mutationFn: () => branchesApi.offer(branch.id, { service: service.id, duration_minutes: Number(duration), price_from: price || null, is_active: active }),
    onSuccess: async () => {
      setSaved(JSON.stringify([duration, price, active]));
      await Promise.all(["services", "branches", "branch-catalog", "branch-configuration", "available-slots"].map(key => cache.invalidateQueries({ queryKey: [key] })));
    } });
  useEffect(() => { onDirtyChange(dirty || mutation.isPending); return () => onDirtyChange(false); }, [dirty, mutation.isPending, onDirtyChange]);
  if (branch.uses_business_defaults) return <p className="text-sm text-platforma-subtle">{t("business.automaticTerms")}</p>;
  return <form className="space-y-3" onSubmit={event => { event.preventDefault(); mutation.mutate(); }}>
    <h3 className="text-sm font-semibold">{t("business.branchTerms")}</h3>
    {mutation.error && <ErrorState error={mutation.error} />}
    <fieldset disabled={disabled || mutation.isPending} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label={t("branches.duration")} required type="number" min={1} max={1440} value={duration} onChange={event => setDuration(event.target.value)} />
        <Input label={t("branches.price")} type="number" min={0} step="0.01" value={price} onChange={event => setPrice(event.target.value)} />
      </div>
      <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />{t("branches.active")}</label>
      <Button type="submit" disabled={!dirty} isLoading={mutation.isPending}>{t("common.save")}</Button>
    </fieldset>
  </form>;
}
