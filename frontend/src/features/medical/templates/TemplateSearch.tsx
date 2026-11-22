import { useState } from "react";
import type { TemplateSearch as Filters } from "../../../api/medicalTemplates";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";

export function TemplateSearch({ value, onApply, disabled = false, approved = false }: {
  value: Filters; onApply: (value: Filters) => void; disabled?: boolean; approved?: boolean;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState(value);
  return <form className="space-y-3" onSubmit={event => { event.preventDefault(); if (!disabled) onApply({ ...draft }); }}
    aria-label={t("medical.templates.search")}>
    <Input label={t("medical.templates.searchText")} value={draft.q ?? ""} maxLength={255}
      onChange={event => setDraft({ ...draft, q: event.target.value })} />
    <div className="grid gap-3 sm:grid-cols-2">
      <Input label={t("medical.templates.category")} value={draft.category ?? ""} maxLength={255}
        onChange={event => setDraft({ ...draft, category: event.target.value })} />
      <Input label={t("medical.templates.specialty")} value={draft.specialty ?? ""} maxLength={255}
        onChange={event => setDraft({ ...draft, specialty: event.target.value })} />
      <Select label={t("medical.templates.language")} value={draft.language ?? ""}
        options={[{ value: "", label: t("medical.templates.allLanguages") }, ...(["ru", "kk", "en"] as const).map(language => ({ value: language, label: t(`language.${language}`) }))]}
        onChange={event => setDraft({ ...draft, language: event.target.value as Filters["language"] })} />
      {approved ? <Select label={t("medical.templates.scope")} value={draft.scope ?? "all"}
        options={(["all", "personal", "common"] as const).map(scope => ({ value: scope, label: t(scope === "all" ? "medical.templates.allAvailable" : `medical.templates.${scope}`) }))}
        onChange={event => setDraft({ ...draft, scope: event.target.value as Filters["scope"] })} /> : null}
    </div>
    <div className="flex flex-wrap gap-2">
      <Button type="submit" variant="secondary" disabled={disabled}>{t("medical.templates.search")}</Button>
      <Button type="button" variant="ghost" disabled={disabled} onClick={() => { setDraft({}); onApply({}); }}>{t("medical.templates.resetSearch")}</Button>
    </div>
  </form>;
}
