import { redactTelemetryUrls, sanitizeTelemetry } from "./telemetryPrivacy";

type PlausibleOptions = { props?: Record<string, unknown>; url: string };
type Plausible = ((event: string, options: PlausibleOptions) => void) & { q?: [string, PlausibleOptions][] };
type PlausibleWindow = Window & { plausible?: Plausible };
let initialized = false;

export function trackPlausibleEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) return;
  (window as PlausibleWindow).plausible?.(redactTelemetryUrls(event), {
    url: redactTelemetryUrls(window.location.href),
    ...(properties ? { props: sanitizeTelemetry(properties) } : {}),
  });
}

export function initPlausibleMonitoring(domain: string | undefined) {
  const target = window as PlausibleWindow;
  if (!domain || initialized || target.plausible || document.querySelector("script[data-domain][src*='plausible']")) return;
  // The legacy manual tracker still reads document.referrer itself and cannot override it.
  if (redactTelemetryUrls(document.referrer) !== document.referrer) return;
  initialized = true;
  const queue: [string, PlausibleOptions][] = [];
  const pending: Plausible = (event, options) => {
    if (queue.length === 100) queue.shift();
    queue.push([event, options]);
  };
  pending.q = queue;
  target.plausible = pending;
  let lastPath: string | undefined;
  const pageview = () => {
    if (lastPath === window.location.pathname) return;
    lastPath = window.location.pathname;
    trackPlausibleEvent("pageview");
  };
  const pushState = window.history.pushState;
  window.history.pushState = function (...args) {
    pushState.apply(this, args);
    pageview();
  };
  window.addEventListener("popstate", pageview);
  window.addEventListener("pageshow", event => { if (event.persisted) { lastPath = undefined; pageview(); } });
  pageview();
  const script = document.createElement("script");
  script.defer = true;
  script.referrerPolicy = "no-referrer";
  script.dataset.domain = domain;
  script.src = "https://plausible.io/js/script.manual.js";
  document.head.appendChild(script);
}
