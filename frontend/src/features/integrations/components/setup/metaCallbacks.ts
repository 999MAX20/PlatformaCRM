export type WhatsAppEmbeddedSignupCallback = {
  type: "zani.whatsapp.embedded_signup_callback";
  code?: string;
  state?: string;
  phone_number_id?: string;
  waba_id?: string;
  display_phone_number?: string;
  cancelled?: boolean;
  coexistence?: boolean;
};

export type InstagramOAuthCallback = {
  type: "zani.instagram.oauth_callback";
  code?: string;
  state?: string;
};

export const whatsappEmbeddedSignupCallbackType = "zani.whatsapp.embedded_signup_callback";
export const instagramOAuthCallbackType = "zani.instagram.oauth_callback";

const facebookSdkUrl = "https://connect.facebook.net/en_US/sdk.js";

declare global {
  interface Window {
    FB?: {
      init: (options: { appId: string; autoLogAppEvents?: boolean; xfbml?: boolean; version: string }) => void;
      login: (
        callback: (response: { authResponse?: { code?: string }; status?: string }) => void,
        options: {
          config_id: string;
          response_type: "code";
          override_default_response_type: true;
          extras: { setup: Record<string, never>; featureType?: "whatsapp_business_app_onboarding"; sessionInfoVersion?: "3" };
        },
      ) => void;
    };
    fbAsyncInit?: () => void;
  }
}

export function parseWhatsAppEmbeddedSignupMessage(event: MessageEvent): WhatsAppEmbeddedSignupCallback | null {
  if (event.origin === window.location.origin && event.data?.type === whatsappEmbeddedSignupCallbackType) {
    return event.data as WhatsAppEmbeddedSignupCallback;
  }

  if (!["https://www.facebook.com", "https://web.facebook.com"].includes(event.origin)) {
    return null;
  }

  const payload = typeof event.data === "string" ? safeParseJson(event.data) : event.data;
  if (payload?.type !== "WA_EMBEDDED_SIGNUP") {
    return null;
  }
  if (["CANCEL", "ERROR"].includes(payload.event)) return { type: whatsappEmbeddedSignupCallbackType, cancelled: true };
  const coexistence = payload.event === "FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING";
  if ((!coexistence && (payload.event !== "FINISH" || typeof payload.data?.phone_number_id !== "string" || !payload.data.phone_number_id))
    || typeof payload.data?.waba_id !== "string" || !payload.data.waba_id) return null;
  return {
    type: whatsappEmbeddedSignupCallbackType,
    phone_number_id: payload.data?.phone_number_id,
    waba_id: payload.data?.waba_id,
    display_phone_number: payload.data?.display_phone_number,
    coexistence,
  };
}

function safeParseJson(value: string) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

let sdkLoading: Promise<void> | undefined;

export async function loadFacebookSdk({ appId, version }: { appId: string; version: string }) {
  if (!window.FB) {
    sdkLoading ??= new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(`script[src="${facebookSdkUrl}"]`);
      const script = existing || document.createElement("script");
      const fail = () => {
        window.clearTimeout(timeout);
        script.remove();
        sdkLoading = undefined;
        reject(new Error("Facebook SDK failed to load."));
      };
      const timeout = window.setTimeout(fail, 15000);
      window.fbAsyncInit = () => {
        window.clearTimeout(timeout);
        if (!window.FB) return fail();
        resolve();
      };
      script.onerror = fail;
      if (!existing) {
        script.async = true;
        script.defer = true;
        script.crossOrigin = "anonymous";
        script.src = facebookSdkUrl;
        document.body.appendChild(script);
      }
    });
    await sdkLoading;
  }
  if (!window.FB) throw new Error("Facebook SDK unavailable.");
  window.FB.init({ appId, autoLogAppEvents: true, xfbml: false, version });
  return window.FB;
}
