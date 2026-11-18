import { googleIntegrationsApi } from "./googleIntegrations";
import type { Id } from "../types";

type PickerResult = { action: string; docs?: { id: string }[] };
type Picker = { setVisible: (value: boolean) => void };
type PickerView = { setMimeTypes: (value: string) => PickerView };
type PickerBuilder = {
  setDeveloperKey(value: string): PickerBuilder;
  setAppId(value: string): PickerBuilder;
  setOAuthToken(value: string): PickerBuilder;
  setOrigin(value: string): PickerBuilder;
  setLocale(value: string): PickerBuilder;
  addView(value: PickerView): PickerBuilder;
  setCallback(value: (result: PickerResult) => void): PickerBuilder;
  build(): Picker;
};
type PickerWindow = Window & {
  gapi?: { load(name: string, options: { callback(): void; onerror(): void; timeout: number; ontimeout(): void }): void };
  google?: { picker: { View: new (name: string) => PickerView; ViewId: { SPREADSHEETS: string }; PickerBuilder: new () => PickerBuilder } };
};
const googleWindow = window as PickerWindow;
let loaded: Promise<void> | undefined;

function loadPicker() {
  if (googleWindow.google?.picker) return Promise.resolve();
  if (loaded) return loaded;
  loaded = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    const fail = () => { script.remove(); reject(new Error("Google Picker could not load.")); };
    const timer = window.setTimeout(fail, 15000);
    script.src = "https://apis.google.com/js/api.js";
    script.async = true;
    script.onerror = () => { window.clearTimeout(timer); fail(); };
    script.onload = () => {
      window.clearTimeout(timer);
      if (!googleWindow.gapi) { fail(); return; }
      googleWindow.gapi.load("picker", { callback: resolve, onerror: fail, timeout: 15000, ontimeout: fail });
    };
    document.head.append(script);
  }).catch(error => { loaded = undefined; throw error; });
  return loaded;
}

export async function chooseGoogleSpreadsheet(connectionId: Id, locale: string): Promise<string | null> {
  await loadPicker();
  const sdk = googleWindow.google?.picker;
  if (!sdk) throw new Error("Google Picker could not load.");
  // Picker needs a short-lived access token; never persist it or place it in query caches.
  const credentials = await googleIntegrationsApi.picker(connectionId);
  return new Promise(resolve => {
    const view = new sdk.View(sdk.ViewId.SPREADSHEETS).setMimeTypes("application/vnd.google-apps.spreadsheet");
    const picker = new sdk.PickerBuilder().setDeveloperKey(credentials.api_key).setAppId(credentials.app_id)
      .setOAuthToken(credentials.access_token).setOrigin(window.location.origin).setLocale(locale)
      .addView(view).setCallback(result => {
        if (result.action === "picked" || result.action === "cancel") {
          picker.setVisible(false);
          resolve(result.action === "picked" ? result.docs?.[0]?.id ?? null : null);
        }
      }).build();
    credentials.access_token = "";
    picker.setVisible(true);
  });
}
