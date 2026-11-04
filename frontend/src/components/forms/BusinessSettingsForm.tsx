import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { getApiFieldErrors } from "../../api/client";
import { getBookingResponsibleOptions } from "../../api/businesses";
import { SettingsFeedback, SettingsSaveBar } from "../../features/settings/components/SettingsLayout";
import { useI18n } from "../../lib/i18n";
import type { Business } from "../../types";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

function createSchema(t: (key: string) => string) {
  return z.object({
    name: z.string().min(2, t("validation.businessName")),
    business_type: z.enum(["dentistry", "beauty", "sauna", "autoservice", "education", "medical", "other"]), city: z.string().optional(), address: z.string().optional(),
    phone: z.string().optional(), whatsapp: z.string().optional(), telegram: z.string().optional(), instagram: z.string().optional(),
    timezone: z.string().min(1, t("settings.redesign.required")),
    currency: z.string().min(1, t("settings.redesign.required")),
    legal_name: z.string().optional(), tax_id: z.string().optional(),
    ai_booking_responsible_user: z.string().optional(),
    invoice_email: z.string().email(t("settings.redesign.invalidEmail")).or(z.literal("")).optional(),
  });
}
type Values = z.infer<ReturnType<typeof createSchema>>;
export function BusinessSettingsForm({ initial, onSubmit }: { initial?: Business | null; onSubmit: (payload: Partial<Business>) => Promise<unknown>; }) {
  const { t } = useI18n();
  const [saveError, setSaveError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  const responsibleOptions = useQuery({ queryKey: ["booking-responsible-options", initial?.id],
    queryFn: () => getBookingResponsibleOptions(initial!.id), enabled: Boolean(initial?.id) });
  const form = useForm<Values>({
    resolver: zodResolver(createSchema(t)), shouldFocusError: false,
    defaultValues: {
      name: initial?.name || "", business_type: initial?.business_type || "other",
      city: initial?.city || "", address: initial?.address || "", phone: initial?.phone || "",
      whatsapp: initial?.whatsapp || "", telegram: initial?.telegram || "", instagram: initial?.instagram || "",
      timezone: initial?.timezone || "Asia/Almaty", currency: initial?.currency || "KZT",
      legal_name: initial?.legal_name || "", tax_id: initial?.tax_id || "", invoice_email: initial?.invoice_email || "",
      ai_booking_responsible_user: initial?.ai_booking_responsible_user ? String(initial.ai_booking_responsible_user) : "",
    },
  });
  function focusField(field: keyof Values) {
    window.requestAnimationFrame(() => form.setFocus(field));
  }
  async function submit(values: Values) {
    setSaveError(null); setSaved(false);
    try {
      const { ai_booking_responsible_user, ...profile } = values;
      await onSubmit({ ...profile, ...(initial?.id ? { ai_booking_responsible_user: ai_booking_responsible_user ? Number(ai_booking_responsible_user) : null } : {}) });
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
    <fieldset disabled={form.formState.isSubmitting} className="space-y-5 p-4 sm:p-5">
      <legend className="sr-only">{t("businessForm.group.profile")}</legend>
      <div className="space-y-3">
        <h2 className="text-base font-bold">{t("settings.redesign.basics")}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label={t("businessForm.name")} {...field("name")} />
          <Select label={t("businessForm.type")} {...field("business_type")} value={form.watch("business_type")}
            options={["dentistry", "beauty", "sauna", "autoservice", "education", "medical", "other"].map(value => ({ value, label: t(`businessType.${value}`) }))} />
          <Input label={t("businessForm.timezone")} placeholder="Asia/Almaty" {...field("timezone")} />
          <Select label={t("businessForm.currency")} {...field("currency")} value={form.watch("currency")} options={["KZT", "USD", "EUR", "RUB"].map(value => ({ value, label: value }))} />
        </div>
      </div>
      {initial?.id ? <div className="space-y-3 border-t border-platforma-border pt-5" aria-busy={responsibleOptions.isPending}>
        <Select label={t("businessForm.aiBookingResponsible")} {...field("ai_booking_responsible_user")}
          onFocus={event => { const trigger = event.currentTarget.nextElementSibling; if (trigger instanceof HTMLButtonElement) trigger.focus(); }}
          value={form.watch("ai_booking_responsible_user") || ""}
          disabled={responsibleOptions.isPending || responsibleOptions.isError}
          options={[
            { value: "", label: responsibleOptions.isPending ? t("common.loading") : t("businessForm.aiBookingUnassigned") },
            ...(initial.ai_booking_responsible_user && !responsibleOptions.data?.some(item => String(item.id) === String(initial.ai_booking_responsible_user))
              ? [{ value: String(initial.ai_booking_responsible_user), label: t("businessForm.aiBookingUnavailable") }] : []),
            ...(responsibleOptions.data ?? []).map(item => ({ value: String(item.id), label: item.label })),
          ]} />
        {responsibleOptions.isError ? <div className="space-y-2"><SettingsFeedback error={responsibleOptions.error} />
          <Button type="button" variant="secondary" onClick={() => void responsibleOptions.refetch()}>{t("common.retry")}</Button></div> : null}
      </div> : null}
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
      <div className="space-y-3 border-t border-platforma-border pt-5">
        <h2 className="text-base font-bold">{t("settings.workflow.companyDetails")}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label={t("businessForm.invoiceEmail")} type="email" {...field("invoice_email")} />
          <Input label={t("businessForm.legalName")} {...field("legal_name")} />
          <Input label={t("settings.workflow.optionalTaxId")} {...field("tax_id")} />
        </div>
      </div>
    </fieldset>
    <SettingsSaveBar feedback={saveError || saved ? <SettingsFeedback error={saveError} saved={saved} /> : form.formState.isDirty ? <p className="text-sm text-platforma-subtle">{t("settings.redesign.unsaved")}</p> : null}>
      <Button type="button" variant="secondary" disabled={form.formState.isSubmitting || !form.formState.isDirty} onClick={() => { form.reset(); setSaveError(null); setSaved(false); }}>{t("common.cancel")}</Button>
      <Button type="submit" disabled={!form.formState.isDirty} isLoading={form.formState.isSubmitting}>{t("businessForm.save")}</Button>
    </SettingsSaveBar>
  </form>;
}
