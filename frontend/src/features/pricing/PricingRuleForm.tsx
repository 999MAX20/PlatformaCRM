import { usePricingRules } from "./usePricingRules";

import { ShieldCheck, SlidersHorizontal } from "lucide-react";
import { type KaspiPricingRule } from "../../api/pricing";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

import { Select } from "../../components/ui/Select";

import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  form: ReturnType<typeof usePricingRules>["form"];
  setForm: ReturnType<typeof usePricingRules>["setForm"];
  canManage: boolean;
  createRule: ReturnType<typeof usePricingRules>["createRule"];
};
export function PricingRuleForm({
  t,
  form,
  setForm,
  canManage,
  createRule,
}: Props) {
  return (
    <section className="rounded-[2rem] border border-platforma-border bg-white p-5 shadow-soft">
      <div className="flex items-center gap-2">
        <ShieldCheck className="text-brand-700" size={20} />
        <h2 className="text-lg font-black text-midnight">
          {t("pricing.newRule")}
        </h2>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Input
          label="SKU"
          value={form.product_sku}
          onChange={(event) =>
            setForm({ ...form, product_sku: event.target.value })
          }
        />
        <Input
          label={t("pricing.name")}
          value={form.product_name}
          onChange={(event) =>
            setForm({ ...form, product_name: event.target.value })
          }
        />
        <Input
          label={t("pricing.currentPrice")}
          value={form.current_price}
          onChange={(event) =>
            setForm({ ...form, current_price: event.target.value })
          }
          type="number"
        />
        <Input
          label={t("pricing.minPrice")}
          value={form.min_price}
          onChange={(event) =>
            setForm({ ...form, min_price: event.target.value })
          }
          type="number"
        />
        <Input
          label={t("pricing.stepBelowCompetitor")}
          value={form.step_amount}
          onChange={(event) =>
            setForm({ ...form, step_amount: event.target.value })
          }
          type="number"
        />
        <Input
          label={t("pricing.dailyChangeLimit")}
          value={form.max_changes_per_day}
          onChange={(event) =>
            setForm({ ...form, max_changes_per_day: event.target.value })
          }
          type="number"
        />
        <Select
          value={form.mode}
          onChange={(event) =>
            setForm({
              ...form,
              mode: event.target.value as KaspiPricingRule["mode"],
            })
          }
          options={[
            { value: "recommend", label: t("pricing.mode.recommend") },
            { value: "approval", label: t("pricing.mode.approval") },
          ]}
        />
      </div>
      <Button
        className="mt-4"
        disabled={
          !canManage ||
          !form.product_sku ||
          !form.current_price ||
          !form.min_price
        }
        isLoading={createRule.isPending}
        onClick={() => createRule.mutate()}
      >
        <SlidersHorizontal size={16} /> {t("pricing.createRule")}
      </Button>
    </section>
  );
}
