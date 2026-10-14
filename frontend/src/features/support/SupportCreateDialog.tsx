import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { normalizeAppError } from "../../api/appError";
import { supportApi } from "../../api/support";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { DraftGuard } from "../../components/actions/DraftGuard";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { SupportCase, SupportScope } from "../../types/support";
import { SupportClinicPicker } from "./SupportClinicPicker";
import { SupportError, useSupportKey } from "./SupportUI";

export function SupportCreateDialog({ scope, initialBusiness, onClose, onCreated }: {
  scope: SupportScope; initialBusiness?: number; onClose: () => void; onCreated: (item: SupportCase) => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const saved = useRef(false);
  const [business, setBusiness] = useState(initialBusiness);
  const [subject, setSubject] = useState("");
  const [text, setText] = useState("");
  const key = useSupportKey();
  const dirty = Boolean(subject.trim() || text.trim());
  const create = useMutation({
    mutationFn: () => {
      const payload = { subject: subject.trim(), text: text.trim(), ...(scope.platform ? { business } : {}) };
      return supportApi.create(scope, payload, key.forPayload(payload));
    },
    onSuccess: item => {
      saved.current = true;
      queryClient.invalidateQueries({ queryKey: ["support"] });
      onCreated(item);
    },
  });
  const error = normalizeAppError(create.error);
  async function close() {
    if (create.isPending) return;
    if (dirty) {
      const result = await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" });
      if (!result.confirmed) return;
    }
    onClose();
  }
  return <>
    <DraftGuard dirty={dirty} pending={create.isPending} saved={saved} />
    <Modal open title={t("supportCases.create")} onClose={() => void close()} closeOnBackdrop={false} testId="support-create-dialog" focusReturnId="support-create-button">
      <form className="space-y-4" onSubmit={event => { event.preventDefault(); create.mutate(); }}>
        {scope.platform && <SupportClinicPicker value={business} onChange={setBusiness} disabled={create.isPending} required />}
        <Input label={t("supportCases.subject")} value={subject} onChange={event => setSubject(event.target.value)} maxLength={200} required disabled={create.isPending} autoFocus={!scope.platform}
          error={create.isError && error.fieldErrors.subject ? t("supportCases.invalidSubject") : undefined} />
        <Textarea label={t("supportCases.description")} value={text} onChange={event => setText(event.target.value)} maxLength={6000} required disabled={create.isPending}
          error={create.isError && error.fieldErrors.text ? t("supportCases.invalidText") : undefined} />
        {create.isError && <SupportError error={create.error} />}
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="ghost" onClick={() => void close()} disabled={create.isPending}>{t("common.cancel")}</Button>
          <Button type="submit" isLoading={create.isPending} disabled={!subject.trim() || !text.trim() || (scope.platform && !business)}>{t("supportCases.submit")}</Button>
        </div>
      </form>
    </Modal>
  </>;
}
