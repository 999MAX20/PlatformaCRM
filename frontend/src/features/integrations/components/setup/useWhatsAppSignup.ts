import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { businessConnectorsApi } from "../../../../api/connectors";
import type { Id } from "../../../../types";
import { loadFacebookSdk, parseWhatsAppEmbeddedSignupMessage } from "./metaCallbacks";

type SignupResult = { state: string; redirect: string; code: string; phone: string; waba: string };
const emptyResult: SignupResult = { state: "", redirect: "", code: "", phone: "", waba: "" };

export function useWhatsAppSignup(businessId: Id, channelId: Id | undefined, notify: (key: string) => void) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState(emptyResult);
  const [pin, setPin] = useState("");
  const [mode, setMode] = useState<"cloud" | "coexistence">("cloud");
  const [phone, setPhone] = useState("");
  const [waiting, setWaiting] = useState(false);
  const generation = useRef(0);
  const active = useRef(false);
  const currentState = useRef("");
  const source = useRef<MessageEventSource | null>(null);
  const retiredSources = useRef(new Set<MessageEventSource>());
  const launchPin = useRef("");
  const launchMode = useRef<"cloud" | "coexistence">("cloud");
  const resultTimeout = useRef<number | undefined>(undefined);
  const notifyRef = useRef(notify);
  notifyRef.current = notify;

  function reset() {
    window.clearTimeout(resultTimeout.current);
    generation.current += 1;
    active.current = false;
    currentState.current = "";
    if (source.current) retiredSources.current.add(source.current);
    source.current = null;
    setResult(emptyResult);
    setWaiting(false);
  }

  useEffect(() => {
    reset();
    setPin("");
    setPhone("");
    setMode("cloud");
    const receive = (event: MessageEvent) => {
      if (!active.current || !event.source || retiredSources.current.has(event.source)) return;
      const payload = parseWhatsAppEmbeddedSignupMessage(event);
      if (!payload) return;
      if (event.origin === window.location.origin && payload.state !== currentState.current) return;
      if (source.current && source.current !== event.source) return;
      source.current = event.source;
      if (payload.cancelled) {
        reset();
        notifyRef.current("integrations.whatsapp.metaAccessDenied");
        return;
      }
      if (!payload.waba_id || (launchMode.current === "coexistence" ? !payload.coexistence : (!payload.phone_number_id || payload.coexistence))) return;
      setResult((previous) => ({ ...previous, phone: payload.phone_number_id || "", waba: payload.waba_id! }));
    };
    window.addEventListener("message", receive);
    return () => {
      window.clearTimeout(resultTimeout.current);
      active.current = false;
      generation.current += 1;
      window.removeEventListener("message", receive);
    };
  }, [businessId, channelId]);

  const start = useMutation({
    mutationFn: async () => {
      if (mode === "coexistence" ? !/^\+[1-9][0-9]{7,14}$/.test(phone) : !/^[0-9]{6}$/.test(pin)) return;
      reset();
      launchPin.current = mode === "cloud" ? pin : "";
      launchMode.current = mode;
      const attempt = generation.current;
      const redirect = `${window.location.origin}/app/ai-agents?zani_provider=whatsapp`;
      const data = await businessConnectorsApi.startWhatsAppEmbeddedSignup({ business: businessId, botChannel: channelId, redirectUri: redirect,
        onboardingMode: mode, expectedPhone: mode === "coexistence" ? phone : undefined });
      if (attempt !== generation.current) return;
      if (!data.app_configured || !data.config_id_configured) {
        notifyRef.current("integrations.whatsapp.metaOpenFailed");
        return;
      }
      const sdk = await loadFacebookSdk({ appId: data.app_id, version: data.graph_api_version });
      if (attempt !== generation.current) return;
      if (!sdk) throw new Error("Facebook SDK unavailable.");
      currentState.current = data.state;
      active.current = true;
      setWaiting(true);
      setResult({ ...emptyResult, state: data.state, redirect: data.redirect_uri });
      sdk.login((response) => {
        if (attempt !== generation.current || !active.current) return;
        const code = response.authResponse?.code;
        if (!code) {
          reset();
          notifyRef.current("integrations.whatsapp.metaAccessDenied");
          return;
        }
        setResult((previous) => previous.code ? previous : { ...previous, code });
        // Meta's exchange code expires after 30 seconds. Never wait for another
        // user action, or retain an incomplete callback indefinitely.
        window.clearTimeout(resultTimeout.current);
        resultTimeout.current = window.setTimeout(() => {
          if (attempt !== generation.current || !active.current) return;
          reset();
          notifyRef.current("integrations.whatsapp.metaSetupIncomplete");
        }, 20000);
      }, {
        config_id: data.config_id, response_type: "code", override_default_response_type: true,
        extras: launchMode.current === "coexistence"
          ? { setup: {}, featureType: "whatsapp_business_app_onboarding", sessionInfoVersion: "3" }
          : { setup: {} },
      });
    },
    onError: () => reset(),
  });

  const complete = useMutation({
    mutationFn: ({ data, registrationPin }: { data: SignupResult; registrationPin: string; attempt: number }) => businessConnectorsApi.completeWhatsAppEmbeddedSignup({
      business: businessId, code: data.code, state: data.state, redirect_uri: data.redirect,
      phone_number_id: data.phone, waba_id: data.waba, registration_pin: registrationPin || undefined,
    }),
    onSuccess: (_, { attempt }) => {
      if (attempt !== generation.current) return;
      reset();
      setPin("");
      notifyRef.current("integrations.whatsapp.connectedNotice");
      queryClient.invalidateQueries({ queryKey: ["bot-channels"] });
      queryClient.invalidateQueries({ queryKey: ["whatsapp-status", channelId] });
      queryClient.invalidateQueries({ queryKey: ["business-connectors"] });
    },
    // A timeout may follow a successful registration. A new attempt rechecks
    // provider state; the consumed authorization code must never be replayed.
    onError: (_, { attempt }) => { if (attempt === generation.current) reset(); },
  });

  const completeSignup = complete.mutate;
  useEffect(() => {
    if (!active.current || !result.code || (!result.phone && launchMode.current === "cloud") || !result.waba) return;
    active.current = false;
    window.clearTimeout(resultTimeout.current);
    setWaiting(false);
    completeSignup({ data: result, registrationPin: launchPin.current, attempt: generation.current });
  }, [result, completeSignup]);

  return {
    start, complete, pin, setPin, mode, setMode, phone, setPhone, waiting, cancel: reset,
    hasResult: Boolean(result.code || result.phone),
    canStart: mode === "coexistence" ? /^\+[1-9][0-9]{7,14}$/.test(phone) : /^[0-9]{6}$/.test(pin),
  };
}
