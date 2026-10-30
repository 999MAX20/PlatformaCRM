import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Dialog } from "../../components/ui/Overlay";
import { Select } from "../../components/ui/Select";

import { Textarea } from "../../components/ui/Textarea";

import { useI18n } from "../../lib/i18n";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  taskModalOpen: boolean;
  setTaskModalOpen: Dispatch<SetStateAction<boolean>>;
  taskDraft: {
    title: string;
    description: string;
    priority: "low" | "normal" | "high" | "urgent";
    due_at: string;
  };
  setTaskDraft: Dispatch<
    SetStateAction<{
      title: string;
      description: string;
      priority: "low" | "normal" | "high" | "urgent";
      due_at: string;
    }>
  >;
  submitTaskFromInspector: () => void;
  createTaskMutation: { isPending: boolean };
};
export function InboxTaskDialog({
  t,
  taskModalOpen,
  setTaskModalOpen,
  taskDraft,
  setTaskDraft,
  submitTaskFromInspector,
  createTaskMutation,
}: Props) {
  return (
    <Dialog
      title={t("conversations.createTaskTitle")}
      focusReturnId="inbox-dialog-actions"
      open={taskModalOpen}
      onClose={() => setTaskModalOpen(false)}
      size="md"
      bodyClassName="space-y-4 bg-platforma-card"
    >
      <Input
        label={t("taskWorkspace.name")}
        value={taskDraft.title}
        onChange={(event) =>
          setTaskDraft((current) => ({
            ...current,
            title: event.target.value,
          }))
        }
        placeholder={t("tasks.titlePlaceholder")}
        autoFocus
      />
      <Textarea
        label={t("taskWorkspace.description")}
        value={taskDraft.description}
        onChange={(event) =>
          setTaskDraft((current) => ({
            ...current,
            description: event.target.value,
          }))
        }
        placeholder={t("tasks.descriptionPlaceholder")}
        rows={4}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Select
          label={t("tasks.priority")}
          value={taskDraft.priority}
          options={[
            { value: "low", label: t("tasks.priorityLow") },
            { value: "normal", label: t("tasks.priorityNormal") },
            { value: "high", label: t("tasks.priorityHigh") },
            { value: "urgent", label: t("tasks.priorityUrgent") },
          ]}
          onChange={(event) =>
            setTaskDraft((current) => ({
              ...current,
              priority: event.target.value as typeof taskDraft.priority,
            }))
          }
        />
        <Input
          label={t("tasks.dueAt")}
          type="datetime-local"
          value={taskDraft.due_at}
          onChange={(event) =>
            setTaskDraft((current) => ({
              ...current,
              due_at: event.target.value,
            }))
          }
        />
      </div>
      <div className="flex justify-end gap-2 border-t border-platforma-border pt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={() => setTaskModalOpen(false)}
        >
          {t("common.cancel")}
        </Button>
        <Button
          type="button"
          onClick={submitTaskFromInspector}
          disabled={!taskDraft.title.trim()}
          isLoading={createTaskMutation.isPending}
        >
          {t("tasks.create")}
        </Button>
      </div>
    </Dialog>
  );
}
