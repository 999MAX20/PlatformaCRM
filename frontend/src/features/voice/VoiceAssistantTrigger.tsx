import { lazy, Suspense, useId, useRef, useState } from "react";
import { useLocation } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Mic, X } from "lucide-react";
import { speechApi } from "../../api/speech";
import { Button } from "../../components/ui/Button";
import { Drawer, OverlayBackdropProvider } from "../../components/ui/Overlay";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useAuth } from "../auth/AuthProvider";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { hasPermission } from "../../lib/permissions";
import { useI18n } from "../../lib/i18n";
import { useVoicePreferences } from "./useVoicePreferences";
import type { Id } from "../../types";
import { voiceBranchContext, voiceCardContext } from "./context";

const VoicePanel = lazy(() => import("./VoicePanel").then(module => ({ default: module.VoicePanel })));
export function VoiceAssistantTrigger({ currentEntity, label, initialConversation }: { currentEntity?: ReturnType<typeof voiceCardContext>; label?: string; initialConversation?: string } = {}) {
  const { user } = useAuth(); const { business } = useActiveBusiness(); const location = useLocation();
  if (!user || !business || !hasPermission(user, business.id, "ai_assistant", "suggest")) return null;
  const reference = currentEntity || voiceCardContext(location.pathname, location.search);
  const card = JSON.stringify(reference);
  const branch = voiceBranchContext(location.pathname, location.search);
  return <ScopedTrigger key={`${user.id}:${business.id}:${location.pathname}:${card}:${branch}:${initialConversation ?? "resume"}`} userId={user.id} businessId={business.id} currentEntity={reference} currentBranch={branch} label={label} initialConversation={initialConversation} />;
}
function ScopedTrigger({ userId, businessId, currentEntity, currentBranch, label, initialConversation }: { userId: Id; businessId: Id; currentEntity?: ReturnType<typeof voiceCardContext>; currentBranch?: number; label?: string; initialConversation?: string }) {
  const panelId = useId();
  const { t } = useI18n(); const { preferences } = useVoicePreferences(userId); const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const status = useQuery({ queryKey: ["voice-status", userId, businessId], queryFn: () => speechApi.status(businessId), enabled: open, retry: false, staleTime: 0 });
  const close = () => { setOpen(false); button.current?.focus(); };
  if (!preferences.visible && !label) return null;
  return <><Button ref={button} variant={label ? "primary" : "ghost"} size={label ? "md" : "icon"} aria-label={label || t("voice.title")} aria-expanded={open} aria-controls={open ? panelId : undefined}
    onClick={() => setOpen(value => !value)}><Mic size={20} aria-hidden="true" />{label}</Button>
    <OverlayBackdropProvider blur={false}><Drawer open={open} onClose={close} id={panelId} ariaLabel={t("voice.title")}
      size="detail" closeOnBackdrop={false} className="h-dvh bg-surface-card">
      <header className="flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-platforma-border px-5"><h2 className="text-lg font-semibold">{t("voice.title")}</h2>
        <Button size="icon" variant="ghost" className="min-h-11 min-w-11" aria-label={t("common.close")} onClick={close}><X size={18} aria-hidden="true" /></Button></header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4">
      {status.isLoading && <LoadingState />}
      {status.error && <ErrorState error={status.error} action={<Button onClick={() => status.refetch()}>{t("common.retry")}</Button>} />}
      {!status.isError && status.data && <Suspense fallback={<LoadingState />}><VoicePanel key={status.data.business} userId={userId} status={status.data} currentEntity={currentEntity} currentBranch={currentBranch} initialConversation={initialConversation} /></Suspense>}
      </div>
    </Drawer></OverlayBackdropProvider></>;
}
