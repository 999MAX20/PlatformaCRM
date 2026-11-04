import { sanitizeTelemetry, redactTelemetryUrls } from "./telemetryPrivacy";
import { initPlausibleMonitoring, trackPlausibleEvent } from "./plausibleMonitoring";

type MonitoringContext = Record<string, unknown>;
type SentryModule = typeof import("@sentry/react");
type PosthogModule = typeof import("posthog-js");

let sentryEnabled = false;
let posthogEnabled = false;
let sentryModule: SentryModule | null = null;
let posthogModule: PosthogModule | null = null;
let sentryPromise: Promise<SentryModule> | null = null;
let posthogPromise: Promise<PosthogModule> | null = null;

export function initFrontendMonitoring() {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
  if (sentryDsn && !sentryPromise) {
    sentryPromise = import("@sentry/react").then((module) => {
      module.init({
        dsn: sentryDsn,
        beforeSend: event => sanitizeTelemetry(event),
        beforeSendTransaction: event => sanitizeTelemetry(event),
        beforeSendSpan: span => sanitizeTelemetry(span),
        beforeBreadcrumb: breadcrumb => sanitizeTelemetry(breadcrumb),
        environment: import.meta.env.MODE,
        tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || 0),
      });
      sentryModule = module;
      sentryEnabled = true;
      return module;
    });
  }

  const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
  if (posthogKey && !posthogPromise) {
    posthogPromise = import("posthog-js").then((module) => {
      module.default.init(posthogKey, {
        api_host: import.meta.env.VITE_POSTHOG_HOST || "https://app.posthog.com",
        capture_pageview: false,
        disable_session_recording: true,
        // Flags transmit initial URL/referrer properties outside before_send.
        advanced_disable_flags: true,
        advanced_disable_feature_flags: true,
        before_send: event => sanitizeTelemetry(event),
      });
      posthogModule = module;
      posthogEnabled = true;
      return module;
    });
  }

  initPlausibleMonitoring(import.meta.env.VITE_PLAUSIBLE_DOMAIN);
}

export function captureFrontendError(error: unknown, context?: MonitoringContext) {
  if (sentryEnabled && sentryModule) {
    sentryModule.captureException(error, context ? { extra: context } : undefined);
    return;
  }
  if (sentryPromise) {
    void sentryPromise.then((module) => module.captureException(error, context ? { extra: context } : undefined));
    return;
  }
  console.error("PlatformaCRM frontend error", error, context);
}

export function trackFrontendEvent(event: string, properties?: MonitoringContext) {
  const safeEvent = redactTelemetryUrls(event);
  const safeProperties = sanitizeTelemetry(properties);
  if (posthogEnabled && posthogModule) posthogModule.default.capture(safeEvent, safeProperties);
  else if (posthogPromise) void posthogPromise.then((module) => module.default.capture(safeEvent, safeProperties));
  trackPlausibleEvent(safeEvent, safeProperties);
}
