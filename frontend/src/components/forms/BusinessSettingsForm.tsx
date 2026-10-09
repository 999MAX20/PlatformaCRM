import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { getApiFieldErrors } from "../../api/client";
import { businessConnectorsApi } from "../../api/connectors";
import { SettingsFeedback, SettingsReference, SettingsSaveBar, SettingsTabs } from "../../features/settings/components/SettingsLayout";
import { useI18n } from "../../lib/i18n";
import type { Business } from "../../types";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

function createSchema(t: (key: string) => string) {
  return z.object({
    name: z.string().min(2, t("validation.businessName")),
    slug: z.string().min(2, t("businessForm.slugRequired")),
    business_type: z.string(), city: z.string().optional(), address: z.string().optional(),
    phone: z.string().optional(), whatsapp: z.string().optional(), telegram: z.string().optional(), instagram: z.string().optional(),
    timezone: z.string().min(1, t("settings.redesign.required")),
    currency: z.string().min(1, t("settings.redesign.required")),
    financial_source_mode: z.enum(["external", "manual"]), financial_connector: z.string().optional(),
    legal_name: z.string().optional(), tax_id: z.string().optional(),
    invoice_email: z.string().email(t("settings.redesign.invalidEmail")).or(z.literal("")).optional(),
  });
}
type Values = z.infer<ReturnType<typeof createSchema>>;
const groups = ["profile", "appointments", "finance", "appearance"] as const;
type Group = (typeof groups)[number];
const fieldGroups: Partial<Record<keyof Values, Group>> = {
  timezone: "appointments", currency: "finance", legal_name: "finance", tax_id: "finance",
  invoice_email: "finance", financial_source_mode: "finance", financial_connector: "finance",
};

export function BusinessSettingsForm({ initial, onSubmit }: { initial?: Business | null; onSubmit: (payload: Partial<Business>) => Promise<unknown>; }) {
  const { t } = useI18n();
  const [activeGroup, setActiveGroup] = useState<Group>("profile");
  const [saveError, setSaveError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  const connectors = useQuery({ queryKey: ["financial-source-options", initial?.id], queryFn: () => businessConnectorsApi.listAll({ business: initial!.id }), enabled: Boolean(initial?.id) });
  const form = useForm<Values>({
    resolver: zodResolver(createSchema(t)), shouldFocusError: false,
    defaultValues: {
      name: initial?.name || "", slug: initial?.slug || "", business_type: initial?.business_type || "other",
      city: initial?.city || "", address: initial?.address || "", phone: initial?.phone || "",
      whatsapp: initial?.whatsapp || "", telegram: initial?.telegram || "", instagram: initial?.instagram || "",
      timezone: initial?.timezone || "Asia/Almaty", currency: initial?.currency || "KZT",
      financial_source_mode: initial?.financial_source_mode || "external",
      financial_connector: initial?.financial_connector ? String(initial.financial_connector) : "",
      legal_name: initial?.legal_name || "", tax_id: initial?.tax_id || "", invoice_email: initial?.invoice_email || "",
    },
  });
  function focusField(field: keyof Values) {
    setActiveGroup(fieldGroups[field] || "profile");
    window.requestAnimationFrame(() => form.setFocus(field));
  }
  async function submit(values: Values) {
    setSaveError(null); setSaved(false);
    try {
      await onSubmit({ ...values, financial_connector: values.financial_source_mode === "external" && values.financial_connector ? Number(values.financial_connector) : null } as Partial<Business>);
      form.reset(values); setSaved(true);
    } catch (error) {
      const fields = Object.entries(getApiFieldErrors(error)).filter(([key]) => key in values);
      if (fields.length) {
        for (const [key, messages] of fields) form.setError(key as keyof Values, { type: "server", message: messages.join(" ") });
        focusField(fields[0][0] as keyof Values);
      } else setSaveError(error);
    }
  }
  const error = (name: keyof Values) => form.formState.errors[name]?.message;
  const field = (name: keyof Values) => ({ ...form.register(name), error: error(name) });
  return <form noValidate onChange={() => setSaved(false)} onSubmit={form.handleSubmit(submit, errors => focusField(Object.keys(errors)[0] as keyof Values))}>
    <div className="px-4 sm:px-5">
      <SettingsTabs value={activeGroup} onChange={setActiveGroup} label={t("settings.section.business-profile")}
        items={groups.map(value => ({ value, label: t(`businessForm.group.${value}`) }))} />
    </div>
    <div className="p-4 sm:p-5">
      <fieldset disabled={form.formState.isSubmitting} hidden={activeGroup !== "profile"} className="space-y-5">
        <legend className="sr-only">{t("businessForm.group.profile")}</legend>
        <div className="space-y-3">
          <h2 className="text-base font-bold">{t("settings.redesign.basics")}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label={t("businessForm.name")} {...field("name")} />
            <Select label={t("businessForm.type")} {...field("business_type")} value={form.watch("business_type")}
              options={["dentistry", "beauty", "sauna", "autoservice", "education", "medical", "other"].map(value => ({ value, label: t(`businessType.${value}`) }))} />
            <Input label={t("businessForm.slug")} {...field("slug")} />
          </div>
        </div>
        <div className="space-y-3 border-t border-platforma-border pt-5">
          <h2 className="text-base font-bold">{t("settings.redesign.contacts")}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label={t("businessForm.city")} {...field("city")} />
            <Input label={t("businessForm.address")} {...field("address")} />
            <Input label={t("businessForm.phone")} type="tel" {...field("phone")} />
            <Input label="WhatsApp" {...field("whatsapp")} />
            <Input label="Telegram" {...field("telegram")} />
            <Input label="Instagram" {...field("instagram")} />
          </div>
        </div>
        <SettingsReference>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div><dt className="text-xs text-platforma-subtle">{t("businessForm.languageMetadata")}</dt><dd className="mt-1 text-sm">{initial?.language || "—"}</dd></div>
            <div><dt className="text-xs text-platforma-subtle">{t("businessForm.slaMinutes")}</dt><dd className="mt-1 text-sm">{initial?.sla_minutes ?? "—"}</dd></div>
          </dl>
          <p className="text-xs leading-5 text-platforma-subtle">{t("businessForm.profileMetadata")}</p>
        </SettingsReference>
      </fieldset>
      <fieldset disabled={form.formState.isSubmitting} hidden={activeGroup !== "appointments"} className="space-y-5">
        <legend className="sr-only">{t("businessForm.group.appointments")}</legend>
        <div className="max-w-md"><Input label={t("businessForm.timezone")} placeholder="Asia/Almaty" {...field("timezone")} /></div>
        <SettingsReference>
          <dl className="space-y-4">
            <div><dt className="text-xs text-platforma-subtle">{t("businessForm.bookingBufferMinutes")}</dt><dd className="mt-1 text-sm">{initial?.booking_buffer_minutes ?? "—"}</dd></div>
            <div><dt className="text-xs text-platforma-subtle">{t("businessForm.cancellationPolicy")}</dt><dd className="mt-1 whitespace-pre-wrap text-sm">{initial?.cancellation_policy || "—"}</dd></div>
          </dl>
          <p className="text-xs leading-5 text-platforma-subtle">{t("businessForm.bookingMetadata")}</p>
        </SettingsReference>
      </fieldset>
      <fieldset disabled={form.formState.isSubmitting} hidden={activeGroup !== "finance"} className="space-y-5">
        <legend className="sr-only">{t("businessForm.group.finance")}</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <Select label={t("businessForm.currency")} {...field("currency")} value={form.watch("currency")} options={["KZT", "USD", "EUR", "RUB"].map(value => ({ value, label: value }))} />
          <Input label={t("businessForm.invoiceEmail")} type="email" {...field("invoice_email")} />
          <Input label={t("businessForm.legalName")} {...field("legal_name")} />
          <Input label={t("businessForm.taxId")} {...field("tax_id")} />
        </div>
        <div className="grid gap-3 border-t border-platforma-border pt-5 sm:grid-cols-2">
          <Select label={t("aiHistory.sourceSetting")} {...field("financial_source_mode")} value={form.watch("financial_source_mode")} options={[{ value: "manual", label: t("aiHistory.manual") }, { value: "external", label: t("aiHistory.external") }]} />
          {form.watch("financial_source_mode") === "external" && <div>
            <Select label={t("aiHistory.integration")} disabled={connectors.isLoading || connectors.isError} {...field("financial_connector")} value={form.watch("financial_connector")}
              options={[{ value: "", label: t("aiHistory.notSelected") }, ...(connectors.data || []).filter(item => item.capability === "finance").map(item => ({ value: String(item.id), label: item.name }))]} />
            {connectors.isError && <div className="mt-2"><p role="alert" className="text-sm text-platforma-danger">{t("aiHistory.integrationUnavailable")}</p><Button variant="ghost" type="button" onClick={() => void connectors.refetch()}>{t("common.retry")}</Button></div>}
          </div>}
        </div>
        <SettingsReference>
          <dl><dt className="text-xs text-platforma-subtle">{t("businessForm.prepaymentPolicy")}</dt><dd className="mt-1 whitespace-pre-wrap text-sm">{initial?.prepayment_policy || "—"}</dd></dl>
          <p className="text-xs leading-5 text-platforma-subtle">{t("businessForm.prepaymentMetadata")}</p>
        </SettingsReference>
      </fieldset>
      <fieldset hidden={activeGroup !== "appearance"} className="space-y-4">
        <legend className="sr-only">{t("businessForm.group.appearance")}</legend>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div><dt className="text-xs text-platforma-subtle">{t("businessForm.brandColor")}</dt><dd className="mt-1 text-sm">{initial?.brand_color || "—"}</dd></div>
          <div><dt className="text-xs text-platforma-subtle">{t("businessForm.brandLogoUrl")}</dt><dd className="mt-1 break-all text-sm">{initial?.brand_logo_url || "—"}</dd></div>
        </dl>
        <p className="text-sm text-platforma-subtle">{t("businessForm.appearanceMetadata")}</p>
      </fieldset>
    </div>
    <SettingsSaveBar feedback={saveError || saved ? <SettingsFeedback error={saveError} saved={saved} /> : form.formState.isDirty ? <p className="text-sm text-platforma-subtle">{t("settings.redesign.unsaved")}</p> : null}>
      <Button type="button" variant="secondary" disabled={form.formState.isSubmitting || !form.formState.isDirty} onClick={() => { form.reset(); setSaveError(null); setSaved(false); }}>{t("common.cancel")}</Button>
      <Button type="submit" disabled={!form.formState.isDirty} isLoading={form.formState.isSubmitting}>{t("businessForm.save")}</Button>
    </SettingsSaveBar>
  </form>;
}
