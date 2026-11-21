import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { clientsApi } from "../../api/clients";
import { normalizeAppError } from "../../api/appError";
import { sourceLabel } from "../../features/clients/utils";
import { useI18n } from "../../lib/i18n";
import type { Client, DuplicateClient, Id } from "../../types";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { ErrorState } from "../ui/StateViews";
import { StatusNotice } from "../ui/StatusNotice";
import { Textarea } from "../ui/Textarea";

function createSchema(t: (key: string) => string) {
  return z.object({
    full_name: z.string().min(2, t("validation.name")),
    phone: z.string().optional(),
    email: z.string().email(t("validation.email")).or(z.literal("")),
    source: z.string(),
    source_detail: z.string().optional(),
    notes: z.string().optional(),
  });
}

type Values = z.infer<ReturnType<typeof createSchema>>;
const clientEditFields = ["full_name", "phone", "email", "source", "source_detail", "notes"] as const;
const fieldLabels = { full_name: "clients.name", phone: "clients.phone", email: "common.email", source: "appointment.source", source_detail: "clients.sourceDetail", notes: "clients.notes" };
function clientValues(client?: Partial<Client>): Values {
  return { full_name: client?.full_name || "", phone: client?.phone || "", email: client?.email || "", source: client?.source || "manual", source_detail: client?.source_detail || "", notes: client?.notes || "" };
}

export function ClientForm({
  businessId,
  initial,
  onSubmit,
  onOpenClient,
  onMergeDuplicate,
  submitError,
  disabled = false,
  showSubmit = true,
  onStateChange,
}: {
  businessId: Id;
  initial?: Partial<Client>;
  disabled?: boolean;
  showSubmit?: boolean;
  onStateChange?: (state: { dirty: boolean; pending: boolean }) => void;
  submitError?: unknown;
  onSubmit: (payload: Partial<Client>) => Promise<unknown>;
  onOpenClient?: (id: Id) => void;
  onMergeDuplicate?: (duplicateId: Id) => Promise<unknown>;
}) {
  const { t } = useI18n();
  const [duplicates, setDuplicates] = useState<DuplicateClient[]>([]);
  const [duplicateError, setDuplicateError] = useState("");
  const [baseline, setBaseline] = useState(initial);
  const [conflict, setConflict] = useState(false);
  const [latest, setLatest] = useState<Client>();
  const [reviewPending, setReviewPending] = useState(false);
  const [localError, setLocalError] = useState<unknown>();
  const [submitted, setSubmitted] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(createSchema(t)),
    defaultValues: {
      full_name: initial?.full_name || "",
      phone: initial?.phone || "",
      email: initial?.email || "",
      source: initial?.source || "manual",
      source_detail: initial?.source_detail || "",
      notes: initial?.notes || "",
    },
  });
  const phone = form.watch("phone");
  const email = form.watch("email");

  async function reviewLatest() {
    if (!initial?.id) return;
    setReviewPending(true);
    setLocalError(undefined);
    try { setLatest(await clientsApi.get(initial.id)); }
    catch (error) { setLocalError(error); }
    finally { setReviewPending(false); }
  }

  function continueEditing() {
    if (!latest) return;
    const draft = form.getValues();
    const previous = clientValues(baseline);
    form.reset(clientValues(latest));
    for (const field of clientEditFields) {
      if (draft[field] !== previous[field]) form.setValue(field, draft[field], { shouldDirty: true });
    }
    setBaseline(latest);
    setConflict(false);
    setLatest(undefined);
    setLocalError(undefined);
    requestAnimationFrame(() => form.setFocus("full_name"));
  }

  useEffect(() => {
    onStateChange?.({ dirty: form.formState.isDirty, pending: form.formState.isSubmitting });
    return () => onStateChange?.({ dirty: false, pending: false });
  }, [form.formState.isDirty, form.formState.isSubmitting, onStateChange]);

  useEffect(() => {
    const hasContact = Boolean(phone?.trim() || email?.trim());
    if (disabled || !hasContact) {
      setDuplicates([]);
      return;
    }
    const timeout = window.setTimeout(() => {
      clientsApi
        .checkDuplicates({
          business: businessId,
          phone,
          email,
          exclude_client_id: initial?.id,
        })
        .then((result) => {
          setDuplicates(result.duplicates);
          setDuplicateError("");
        })
        .catch(() => setDuplicateError(t("clients.duplicateError")));
    }, 450);
    return () => window.clearTimeout(timeout);
  }, [businessId, disabled, email, initial?.id, phone, t]);

  return (
    <form
      data-testid="client-action-form"
      className="grid gap-4"
      onSubmit={form.handleSubmit(async (values) => {
        if (disabled || conflict || reviewPending) return;
        setSubmitted(true);
        setLocalError(undefined);
        try {
          const previous = clientValues(baseline);
          const payload = initial?.id
            ? { ...Object.fromEntries(clientEditFields.filter(field => values[field] !== previous[field]).map(field => [field, values[field]])), expected_updated_at: baseline?.updated_at }
            : { ...values, business: businessId };
          await onSubmit(payload as Partial<Client>);
        } catch (error) {
          if (normalizeAppError(error).code === "client_edit_conflict") {
            setConflict(true);
            setLatest(undefined);
          } else setLocalError(error);
        }
      })}
    >
      <fieldset disabled={disabled || reviewPending || form.formState.isSubmitting} className="grid gap-4">
      <Input label={t("clients.name")} error={form.formState.errors.full_name?.message} {...form.register("full_name")} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label={t("clients.phone")} {...form.register("phone")} />
        <Input label={t("common.email")} error={form.formState.errors.email?.message} {...form.register("email")} />
      </div>
      {duplicates.length ? (
        <StatusNotice
          tone="warning"
          title={t("clients.duplicateTitle")}
          description={t("clients.duplicateText")}
          details={<div className="space-y-2">
            {duplicates.filter((client): client is DuplicateClient & { id: Id } => client.id !== null).slice(0, 3).map((client) => (
              <div key={client.id} className="flex flex-wrap items-center justify-between gap-2 rounded-control border border-platforma-warning/[0.18] bg-surface-card p-3">
                <span className="font-semibold">{client.full_name} · {client.phone || client.email || t("clients.noContact")}</span>
                {onOpenClient ? (
                  <Button type="button" variant="secondary" className="h-9 rounded-xl px-3 text-xs" onClick={() => onOpenClient(client.id)}>
                    {t("clients.openExisting")}
                  </Button>
                ) : null}
                {initial && onMergeDuplicate ? (
                  <Button type="button" variant="ghost" className="h-9 rounded-xl px-3 text-xs" onClick={() => onMergeDuplicate(client.id)}>
                    {t("clients.mergeCurrent")}
                  </Button>
                ) : null}
              </div>
            ))}
          </div>}
        />
      ) : null}
      {duplicateError ? <ErrorState message={duplicateError} /> : null}
      <Select
        label={t("appointment.source")}
        options={[
          { value: "manual", label: t("clients.sourceManual") },
          { value: "website", label: t("clients.sourceWebsite") },
          { value: "telegram", label: "Telegram" },
          { value: "whatsapp", label: "WhatsApp" },
          { value: "instagram", label: "Instagram" },
          { value: "parser", label: t("clients.sourceParser") },
          { value: "other", label: t("clients.sourceOther") },
        ]}
        {...form.register("source")}
        value={form.watch("source")}
      />
      <Input label={t("clients.sourceDetail")} {...form.register("source_detail")} />
      <Textarea label={t("clients.notes")} {...form.register("notes")} />
      {conflict && <StatusNotice tone="warning" title={t("clients.editConflictTitle")} description={t("clients.editConflictDescription")}
        details={latest ? <dl className="space-y-2 break-words">{clientEditFields.map(field => <div key={field}><dt className="font-semibold">{t(fieldLabels[field])}</dt><dd className="whitespace-pre-wrap">{field === "source" ? sourceLabel(latest.source, t) : latest[field] || "—"}</dd></div>)}</dl> : undefined}
        action={latest
          ? <Button type="button" variant="secondary" size="lg" onClick={continueEditing}>{t("clients.editConflictContinue")}</Button>
          : <Button type="button" variant="secondary" size="lg" isLoading={reviewPending} onClick={() => void reviewLatest()}>{t("clients.editConflictReview")}</Button>} />}
      {localError || (!submitted && submitError) ? <ErrorState error={localError || submitError} /> : null}
      {showSubmit && <Button data-testid="client-action-submit" type="submit" disabled={conflict || reviewPending} isLoading={form.formState.isSubmitting}>{duplicates.length && !initial ? t("clients.createAnyway") : t("clients.save")}</Button>}
      </fieldset>
    </form>
  );
}
