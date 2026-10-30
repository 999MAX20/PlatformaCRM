import { useLeadCardQueue } from "../../../features/leads/hooks/useLeadCardQueue";
import { LeadOfflineQueueStatus } from "../../../features/leads/components/LeadOfflineQueueStatus";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { StickyNote } from "lucide-react";
import { useState } from "react";
import { notesApi } from "../../../api/activities";
import { appointmentsApi } from "../../../api/appointments";
import { leadsApi } from "../../../api/leads";
import { formatDateTime } from "../../../lib/format";
import { useI18n } from "../../../lib/i18n";
import type { CrmCardPayload } from "../../../types";
import { Button } from "../../ui/Button";
import { ErrorState } from "../../ui/StateViews";
import { Textarea } from "../../ui/Textarea";
import { drawerSurfaceClass, EmptyBlock } from "./shared";
import type { CrmDrawerEntity } from "./types";

export function EntityNotesPanel({ data, entity }: { data: CrmCardPayload; entity: CrmDrawerEntity }) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const businessId = data.client?.business || data.lead?.business || data.deal?.business || data.appointment?.business;
  const entityType = entity.type.charAt(0).toUpperCase() + entity.type.slice(1);
  const offline = useLeadCardQueue(entity.type === "lead" ? data.lead?.business : undefined);
  const mutation = useMutation({
    networkMode: entity.type === "lead" ? "always" : "online",
    mutationFn: async () => {
      const noteText = text.trim();
      if (!noteText) throw new Error("Note text is required.");
      if (entity.type === "lead" && data.lead) {
        if (!navigator.onLine) {
          await offline.enqueueOfflineAction({ id: crypto.randomUUID(), type: "note", leadId: data.lead.id,
            text: noteText, createdAt: new Date().toISOString() });
          return;
        }
        return leadsApi.addNote({ id: data.lead.id, text: noteText });
      }
      if (entity.type === "appointment" && data.appointment) {
        return appointmentsApi.addNote({ id: data.appointment.id, text: noteText });
      }
      if (!businessId) throw new Error("Business is required.");
      return notesApi.create({
        business: businessId,
        client: data.client?.id || null,
        entity_type: entityType,
        entity_id: String(entity.id),
        text: noteText,
      });
    },
    onSuccess: () => {
      setText("");
      queryClient.invalidateQueries({ queryKey: ["crm-card", entity.type, entity.id] });
      queryClient.invalidateQueries({ queryKey: ["activity-events"] });
    },
  });

  return (
    <div className="space-y-3">
      <LeadOfflineQueueStatus queue={offline.offlineQueue} recover={offline.recoverOfflineAction} storageError={offline.storageError} syncing={offline.syncing} online={offline.isOnline} />
      <div className={drawerSurfaceClass}>
        <h3 className="font-semibold text-platforma-ink">{t("crmCard.comment")}</h3>
        <p className="mt-1 text-sm leading-6 text-platforma-muted">{t("crmCard.commentText")}</p>
        <Textarea className="mt-3" value={text} onChange={(event) => setText(event.target.value)} placeholder={t("crmCard.commentPlaceholder")} />
        <div className="mt-3 flex justify-end">
          <Button type="button" variant="secondary" isLoading={mutation.isPending} onClick={() => mutation.mutate()}>
            {t("crmCard.addComment")}
          </Button>
        </div>
        {mutation.error ? <div className="mt-2"><ErrorState message={t("crmCard.commentError")} /></div> : null}
      </div>
      {data.notes.map((note) => (
        <div key={note.id} className={drawerSurfaceClass}>
          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-platforma-faint">
            <StickyNote size={14} /> {t("crmCard.note")} · {formatDateTime(note.created_at)}
          </div>
          <p className="text-sm leading-6 text-platforma-text">{note.text}</p>
        </div>
      ))}
      {!data.notes.length ? <EmptyBlock title={t("crmCard.noNotes")} text={t("crmCard.noNotesText")} /> : null}
    </div>
  );
}
