import { useEffect, useRef, type RefObject } from "react";
import { useBlocker } from "react-router";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { useI18n } from "../../../lib/i18n";

export function TaskDraftGuard({ dirty, pending, saved }: { dirty: boolean; pending: boolean; saved?: RefObject<boolean> }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const confirming = useRef(false);
  const blocker = useBlocker(() => !saved?.current && (dirty || pending));
  useEffect(() => {
    const unload = (event: BeforeUnloadEvent) => { if (!saved?.current && (dirty || pending)) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", unload);
    return () => window.removeEventListener("beforeunload", unload);
  }, [dirty, pending, saved]);
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (pending) return;
    if (!dirty || saved?.current) { blocker.proceed(); return; }
    if (confirming.current) return;
    confirming.current = true;
    void confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" }).then(({ confirmed }) => {
      confirming.current = false;
      if (confirmed) blocker.proceed(); else blocker.reset();
    });
  }, [blocker, confirm, dirty, pending, saved, t]);
  return null;
}
