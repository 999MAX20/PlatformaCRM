import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useState } from "react";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { businessConnectorsApi } from "../../api/connectors";

import { useI18n } from "../../lib/i18n";
import type { Business } from "../../types";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Textarea } from "../ui/Textarea";

function createSchema(t: (key: string) => string) {
  return z.object({
    name: z.string().min(2, t("validation.businessName")),
    slug: z.string().min(2, t("businessForm.slugRequired")),
    business_type: z.string(),
    city: z.string().optional(),
    address: z.string().optional(),
    phone: z.string().optional(),
    whatsapp: z.string().optional(),
    telegram: z.string().optional(),
    instagram: z.string().optional(),
    timezone: z.string().min(1),
    currency: z.string().min(1),
    financial_source_mode: z.enum(["external", "manual"]),
    financial_connector: z.string().optional(),
    legal_name: z.string().optional(),
    tax_id: z.string().optional(),
    invoice_email: z.string().email().or(z.literal("")).optional(),
  });
}

type Values = z.infer<ReturnType<typeof createSchema>>;
const groups = ["profile", "appointments", "finance", "appearance"] as const;
type Group = (typeof groups)[number];
const fieldGroups: Partial<Record<keyof Values, Group>> = {
  timezone: "appointments",
  currency: "finance", legal_name: "finance", tax_id: "finance", invoice_email: "finance",
  financial_source_mode: "finance", financial_connector: "finance",
};

export function BusinessSettingsForm({
  initial,
  onSubmit,
}: {
  initial?: Business | null;
  onSubmit: (payload: Partial<Business>) => Promise<unknown>;
}) {
  const { t } = useI18n();
  const [activeGroup, setActiveGroup] = useState<Group>("profile");
  const connectors = useQuery({ queryKey: ["financial-source-options", initial?.id], queryFn: () => businessConnectorsApi.listAll({ business: initial!.id }), enabled: Boolean(initial?.id) });
  const form = useForm<Values>({
    resolver: zodResolver(createSchema(t)),
    shouldFocusError: false,
    defaultValues: {
      name: initial?.name || "",
      slug: initial?.slug || "",
      business_type: initial?.business_type || "other",
      city: initial?.city || "",
      address: initial?.address || "",
      phone: initial?.phone || "",
      whatsapp: initial?.whatsapp || "",
      telegram: initial?.telegram || "",
      instagram: initial?.instagram || "",
      timezone: initial?.timezone || "Asia/Almaty",
      currency: initial?.currency || "KZT",
      financial_source_mode: initial?.financial_source_mode || "external",
      financial_connector: initial?.financial_connector ? String(initial.financial_connector) : "",
      legal_name: initial?.legal_name || "",
      tax_id: initial?.tax_id || "",
      invoice_email: initial?.invoice_email || "",
    },
  });

  return (
    <form className="grid gap-4" onSubmit={form.handleSubmit(
      (values) => onSubmit({ ...values, financial_connector: values.financial_source_mode === "external" && values.financial_connector ? Number(values.financial_connector) : null } as Partial<Business>),
      (errors) => {
        const field = Object.keys(errors)[0] as keyof Values;
        setActiveGroup(fieldGroups[field] || "profile");
        window.requestAnimationFrame(() => form.setFocus(field));
      },
    )}>
      <div className="grid grid-cols-2 gap-1 rounded-control bg-surface-muted p-1 lg:grid-cols-4">
        {groups.map((group) => <button key={group} type="button" aria-pressed={activeGroup === group}
          className={`platforma-focus-ring min-h-10 rounded-control px-3 py-2 text-sm font-semibold ${activeGroup === group ? "bg-surface-card text-brand-700 shadow-xs" : "text-platforma-subtle hover:bg-surface-hover"}`}
          onClick={() => setActiveGroup(group)}>{t(`businessForm.group.${group}`)}</button>)}
      </div>
      <fieldset hidden={activeGroup !== "profile"} className="space-y-4">
      <legend className="sr-only">{t("businessForm.group.profile")}</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("businessForm.name")} error={form.formState.errors.name?.message} {...form.register("name")} />
        <Input label={t("businessForm.slug")} error={form.formState.errors.slug?.message} {...form.register("slug")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Select label={t("businessForm.type")} options={[
          { value: "dentistry", label: t("businessType.dentistry") },
          { value: "beauty", label: t("businessType.beauty") },
          { value: "sauna", label: t("businessType.sauna") },
          { value: "autoservice", label: t("businessType.autoservice") },
          { value: "education", label: t("businessType.education") },
          { value: "medical", label: t("businessType.medical") },
          { value: "other", label: t("businessType.other") },
        ]} {...form.register("business_type")} value={form.watch("business_type")} />
        <Input label={t("businessForm.languageMetadata")} value={initial?.language || "—"} readOnly />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("businessForm.city")} {...form.register("city")} />
        <Input label={t("businessForm.address")} {...form.register("address")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("businessForm.phone")} {...form.register("phone")} />
        <Input label="WhatsApp" {...form.register("whatsapp")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Telegram" {...form.register("telegram")} />
        <Input label="Instagram" {...form.register("instagram")} />
      </div>
      <Input label={t("businessForm.slaMinutes")} value={initial?.sla_minutes ?? "—"} readOnly />
      <p className="text-sm text-platforma-subtle">{t("businessForm.profileMetadata")}</p>
      </fieldset>
      <fieldset hidden={activeGroup !== "appointments"} className="space-y-4">
        <legend className="sr-only">{t("businessForm.group.appointments")}</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label={t("businessForm.timezone")} placeholder="Asia/Almaty" {...form.register("timezone")} />
          <Input label={t("businessForm.bookingBufferMinutes")} value={initial?.booking_buffer_minutes ?? "—"} readOnly />
        </div>
        <Textarea label={t("businessForm.cancellationPolicy")} rows={3} value={initial?.cancellation_policy || ""} readOnly />
        <p className="text-sm text-platforma-subtle">{t("businessForm.bookingMetadata")}</p>
      </fieldset>
      <fieldset hidden={activeGroup !== "finance"} className="space-y-4">
      <legend className="sr-only">{t("businessForm.group.finance")}</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <Select label={t("businessForm.currency")} options={[
          { value: "KZT", label: "KZT" },
          { value: "USD", label: "USD" },
          { value: "EUR", label: "EUR" },
          { value: "RUB", label: "RUB" },
        ]} {...form.register("currency")} value={form.watch("currency")} />
        <Input label={t("businessForm.invoiceEmail")} error={form.formState.errors.invoice_email?.message} {...form.register("invoice_email")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("businessForm.legalName")} {...form.register("legal_name")} />
        <Input label={t("businessForm.taxId")} {...form.register("tax_id")} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Select label={t("aiHistory.sourceSetting")} options={[{ value: "manual", label: t("aiHistory.manual") }, { value: "external", label: t("aiHistory.external") }]} {...form.register("financial_source_mode")} value={form.watch("financial_source_mode")} />
        {form.watch("financial_source_mode") === "external" && <Select label={t("aiHistory.integration")} disabled={connectors.isLoading || connectors.isError} options={[{ value: "", label: t("aiHistory.notSelected") }, ...(connectors.data || []).filter(item => item.capability === "finance").map(item => ({ value: String(item.id), label: item.name }))]} {...form.register("financial_connector")} value={form.watch("financial_connector")} />}
      </div>
      {connectors.isError && form.watch("financial_source_mode") === "external" && <p role="alert" className="text-sm text-platforma-danger">{t("aiHistory.integrationUnavailable")}</p>}
      <Textarea label={t("businessForm.prepaymentPolicy")} rows={3} value={initial?.prepayment_policy || ""} readOnly />
      <p className="text-sm text-platforma-subtle">{t("businessForm.prepaymentMetadata")}</p>
      </fieldset>
      <fieldset hidden={activeGroup !== "appearance"} className="space-y-4">
      <legend className="sr-only">{t("businessForm.group.appearance")}</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("businessForm.brandColor")} value={initial?.brand_color || ""} readOnly />
        <Input label={t("businessForm.brandLogoUrl")} value={initial?.brand_logo_url || ""} readOnly />
      </div>
      <p className="text-sm text-platforma-subtle">{t("businessForm.appearanceMetadata")}</p>
      </fieldset>
      <div className="sticky bottom-0 flex justify-end border-t border-platforma-border bg-surface-card py-3">
        <Button type="submit" className="w-full sm:w-auto" isLoading={form.formState.isSubmitting}>{t("businessForm.save")}</Button>
      </div>
    </form>
  );
}
