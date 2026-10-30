import { useAutomationEditor } from "./useAutomationEditor";

import { Button } from "../../components/ui/Button";

import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";

import { Select } from "../../components/ui/Select";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";

type Props = {
  t: ReturnType<typeof useI18n>["t"];
  createOpen: ReturnType<typeof useAutomationEditor>["createOpen"];
  setCreateOpen: ReturnType<typeof useAutomationEditor>["setCreateOpen"];
  mutation: ReturnType<typeof useAutomationEditor>["mutation"];
  business: ReturnType<typeof useActiveBusiness>["business"];
  form: ReturnType<typeof useAutomationEditor>["form"];
  setForm: ReturnType<typeof useAutomationEditor>["setForm"];
  triggers: { value: string; label: string }[];
};
export function AutomationCreateDialog({
  t,
  createOpen,
  setCreateOpen,
  mutation,
  business,
  form,
  setForm,
  triggers,
}: Props) {
  return (
    <Modal
      title={t("automations.createRule")}
      open={createOpen}
      onClose={() => setCreateOpen(false)}
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate({
            business: business.id,
            name: form.name,
            trigger_type: form.trigger_type,
            description: form.description,
            is_active: false,
          });
        }}
      >
        <Input
          label={t("automations.name")}
          placeholder={t("automations.ruleNamePlaceholder")}
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
          required
        />
        <Select
          label={t("automations.trigger")}
          value={form.trigger_type}
          onChange={(event) =>
            setForm({ ...form, trigger_type: event.target.value })
          }
          options={triggers}
        />
        <Input
          label={t("automations.descriptionLabel")}
          placeholder={t("automations.descriptionPlaceholder")}
          value={form.description}
          onChange={(event) =>
            setForm({ ...form, description: event.target.value })
          }
        />
        <Button type="submit" isLoading={mutation.isPending}>
          {t("automations.saveDraft")}
        </Button>
      </form>
    </Modal>
  );
}
