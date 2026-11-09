import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Mic, X } from "lucide-react";
import { speechApi } from "../../api/speech";
import { Button } from "../../components/ui/Button";
import { PopoverSurface } from "../../components/ui/Overlay";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { hasPermission } from "../../lib/permissions";
import { useI18n } from "../../lib/i18n";
import { useVoicePreferences } from "./useVoicePreferences";
import type { Id } from "../../types";
import { voiceBranchContext, voiceCardContext } from "./context";

const VoicePanel = lazy(() => import("./VoicePanel").then(module => ({ default: module.VoicePanel })));
export function VoiceAssistantTrigger({ currentEntity }: { currentEntity?: ReturnType<typeof voiceCardContext> } = {}) {
  const { user } = useAuth(); const { business } = useActiveBusiness(); const location = useLocation();
  if (!user || !business || !hasPermission(user, business.id, "ai_assistant", "suggest")) return null;
  const reference = currentEntity || voiceCardContext(location.pathname, location.search);
  const card = JSON.stringify(reference);
  const branch = voiceBranchContext(location.pathname, location.search);
  return <ScopedTrigger key={`${user.id}:${business.id}:${location.pathname}:${card}:${branch}`} userId={user.id} businessId={business.id} currentEntity={reference} currentBranch={branch} />;
}
function ScopedTrigger({ userId, businessId, currentEntity, currentBranch }: { userId: Id; businessId: Id; currentEntity?: ReturnType<typeof voiceCardContext>; currentBranch?: number }) {
  const { t } = useI18n(); const { preferences } = useVoicePreferences(userId); const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null); const panel = useRef<HTMLDivElement>(null);
  const status = useQuery({ queryKey: ["voice-status", userId, businessId], queryFn: () => speechApi.status(businessId), enabled: open, retry: false, staleTime: 0 });
  const close = () => { setOpen(false); button.current?.focus(); };
  useEffect(() => {
    if (!open) return;
    panel.current?.focus();
    const outside = (event: PointerEvent) => { if (!panel.current?.contains(event.target as Node) && !button.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented && !document.querySelector('[role="dialog"][aria-modal="true"]')) {
        event.preventDefault(); close();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  if (!preferences.visible) return null;
  return <><Button ref={button} variant="ghost" size="icon" aria-label={t("voice.title")} aria-expanded={open} aria-controls={open ? "voice-panel" : undefined}
    onClick={() => setOpen(value => !value)}><Mic size={20} aria-hidden="true" /></Button>
    {open && createPortal(<PopoverSurface ref={panel} id="voice-panel" role="dialog" aria-label={t("voice.title")} tabIndex={-1}
      className="fixed inset-x-2 top-16 z-[80] max-h-[calc(100dvh-5rem)] overflow-y-auto bg-surface-card p-4 shadow-premium sm:left-auto sm:right-4 sm:w-[400px]"
      onKeyDown={event => { if (event.key === "Escape" && !event.defaultPrevented) { event.preventDefault(); event.stopPropagation(); close(); } }}>
      <header className="mb-2 flex items-center justify-between gap-3"><h2 className="text-sm font-medium">{t("voice.title")}</h2>
        <Button size="icon" variant="ghost" aria-label={t("common.close")} onClick={close}><X size={18} aria-hidden="true" /></Button></header>
      {status.isLoading && <LoadingState />}
      {status.error && <ErrorState error={status.error} action={<Button onClick={() => status.refetch()}>{t("common.retry")}</Button>} />}
      {!status.isError && status.data && <Suspense fallback={<LoadingState />}><VoicePanel key={status.data.business} userId={userId} status={status.data} currentEntity={currentEntity} currentBranch={currentBranch} /></Suspense>}
    </PopoverSurface>, button.current?.closest('[role="dialog"][aria-modal="true"]') || document.body)}</>;
}
