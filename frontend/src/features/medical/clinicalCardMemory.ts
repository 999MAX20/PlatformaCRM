import type { HistoryNavigation } from "./clinicalHistoryNavigation";
import type { ViewMemory } from "./clinicalViewNavigation";

export type ClinicalTab = "overview" | "encounter" | "history" | "teeth" | "plan" | "documents" | "orders";
type CardMemory = { tab: ClinicalTab; history: Map<string, HistoryNavigation>; views: ViewMemory };
let activeOwner = "";
const cards = new Map<number, CardMemory>();

// Only navigation survives closing a card. Clinical responses and drafts never enter this cache.
export function clinicalCardMemory(owner: string, appointmentId: number): CardMemory {
  if (activeOwner !== owner) { cards.clear(); activeOwner = owner; }
  let memory = cards.get(appointmentId);
  if (!memory) {
    if (cards.size >= 32) cards.delete(cards.keys().next().value!);
    memory = { tab: "encounter", history: new Map(), views: { teeth: new Map(), plans: new Map() } };
    cards.set(appointmentId, memory);
  }
  return memory;
}
