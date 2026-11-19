import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { isMfaPendingResponse } from "../../api/auth";
import { teamApi } from "../../api/team";
import { rememberInvitationBusiness } from "../../lib/invitationBusiness";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "./AuthProvider";

type Preview = Awaited<ReturnType<typeof teamApi.previewInvitation>>;
export type InvitationValues = { full_name?: string; phone?: string; password?: string };

export function useInvitationEntry(token: string, preview?: Preview) {
  const { login, refreshUser } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [mfa, setMfa] = useState(false);
  const acceptedToken = useRef<string | null>(null);
  const [needsLogin, setNeedsLogin] = useState(false);

  async function enter() {
    const current = await refreshUser();
    if (!current || !preview || current.email.trim().toLowerCase() !== preview.email.trim().toLowerCase()
      || !current.businesses.some(item => String(item.id) === String(preview.business))) throw new Error(t("invite.accessUnavailable"));
    rememberInvitationBusiness(current.id, preview.business);
    queryClient.clear();
    navigate("/app", { replace: true });
  }

  async function accept(values: InvitationValues = {}) {
    if (acceptedToken.current === token || preview?.status === "accepted") return;
    await teamApi.acceptInvitation({ token, ...values });
    acceptedToken.current = token;
  }

  const mutation = useMutation({
    onError: () => { void queryClient.invalidateQueries({ queryKey: ["team-invitation-preview", token] }); },
    mutationFn: async ({ values = {}, authenticated = false }: { values?: InvitationValues; authenticated?: boolean }) => {
      if (!preview) return;
      if (!authenticated) {
        // Existing accounts use the ordinary password/MFA session flow. New
        // accounts first consume the invite, then sign in with the chosen password.
        if (!preview.requires_authentication && acceptedToken.current !== token) await accept(values);
        setNeedsLogin(true);
        const result = await login(preview.email, values.password || "");
        if (isMfaPendingResponse(result)) {
          sessionStorage.setItem("zani_mfa_pending", JSON.stringify(result));
          setMfa(true);
          return;
        }
        setNeedsLogin(false);
      }
      await accept();
      await enter();
    },
  });
  async function completeMfa() {
    setNeedsLogin(false);
    await accept();
    await enter();
  }
  return { mutation, mfa, completeMfa, needsLogin, hasAccepted: acceptedToken.current === token || preview?.status === "accepted" };
}
