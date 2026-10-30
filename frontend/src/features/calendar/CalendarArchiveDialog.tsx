import { useCalendarCommands } from "./useCalendarCommands";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";

import { useI18n } from "../../lib/i18n";

import type { Appointment } from "../../types";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  archiveTarget: Appointment | null;
  setArchiveTarget: Dispatch<SetStateAction<Appointment | null>>;
  setArchiveReason: Dispatch<SetStateAction<string>>;
  archiveReason: string;
  archiveMutation: ReturnType<typeof useCalendarCommands>["archiveMutation"];
};
export function CalendarArchiveDialog({
  t,
  archiveTarget,
  setArchiveTarget,
  setArchiveReason,
  archiveReason,
  archiveMutation,
}: Props) {
  return (
    <Modal
      title={t("appointments.archive")}
      open={Boolean(archiveTarget)}
      onClose={() => {
        setArchiveTarget(null);
        setArchiveReason("");
      }}
    >
      <div className="space-y-4">
        <Input
          label={t("appointments.archiveReason")}
          value={archiveReason}
          onChange={(event) => setArchiveReason(event.target.value)}
          placeholder={t("appointments.archiveReasonPlaceholder")}
        />
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setArchiveTarget(null);
              setArchiveReason("");
            }}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            variant="warning"
            isLoading={archiveMutation.isPending}
            onClick={() => {
              if (!archiveTarget) return;
              archiveMutation.mutate({
                id: archiveTarget.id,
                reason:
                  archiveReason.trim() ||
                  t("appointments.archiveReasonDefault"),
              });
            }}
          >
            {t("appointments.archive")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
