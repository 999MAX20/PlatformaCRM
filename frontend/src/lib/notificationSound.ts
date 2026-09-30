import { useSyncExternalStore } from "react";
import type { Id } from "../types";

const changeEvent = "platforma:notification-sound";
let context: AudioContext | null = null;

function preferenceKey(userId: Id) {
  return `platforma:notification-sound:${userId}`;
}

function subscribe(listener: () => void) {
  window.addEventListener(changeEvent, listener);
  window.addEventListener("storage", listener);
  return () => {
    window.removeEventListener(changeEvent, listener);
    window.removeEventListener("storage", listener);
  };
}

export function useNotificationSoundPreference(userId?: Id) {
  return useSyncExternalStore(subscribe, () => {
    try { return Boolean(userId && localStorage.getItem(preferenceKey(userId)) === "on"); }
    catch { return false; }
  }, () => false);
}

export function setNotificationSoundPreference(userId: Id, enabled: boolean) {
  localStorage.setItem(preferenceKey(userId), enabled ? "on" : "off");
  window.dispatchEvent(new Event(changeEvent));
}

export async function unlockNotificationSound() {
  if (!context || context.state === "closed") context = new AudioContext();
  if (context.state === "suspended") await context.resume();
  return context.state === "running";
}

// A quiet two-note chime with a soft attack and decay; generated locally.
// No remote audio assets, microphone access or additional dependencies.
export function playNotificationSound() {
  if (!context || context.state !== "running") return false;
  const start = context.currentTime;
  for (const [index, frequency] of [659.25, 880].entries()) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const at = start + index * 0.13;
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0, at);
    gain.gain.linearRampToValueAtTime(0.065, at + 0.018);
    gain.gain.exponentialRampToValueAtTime(0.001, at + 0.28);
    gain.gain.linearRampToValueAtTime(0, at + 0.32);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    oscillator.start(at);
    oscillator.stop(at + 0.33);
  }
  return true;
}
