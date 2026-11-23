import { useState } from "react";
import type { ClinicalHistoryFilters, ClinicalReadScope } from "../../api/medicalClinical";

type RevisionNavigation = { cursor?: number; selected?: number };
export type HistoryNavigation = { filters: ClinicalHistoryFilters; input: ClinicalHistoryFilters;
  cursor?: number; selected?: number; revisions: Record<number, RevisionNavigation> };
export type HistoryMemory = { current: Map<string, HistoryNavigation> };

export function historyScopeKey(scope: ClinicalReadScope) {
  return `${scope.business_id}:${scope.patient_id}:${scope.appointment_id ?? ""}:${scope.participation_id ?? ""}`;
}

export function useHistoryNavigation(scope: ClinicalReadScope, memory?: HistoryMemory) {
  const key = historyScopeKey(scope);
  const [navigation, setNavigation] = useState<HistoryNavigation>(() => memory?.current.get(key) ?? { filters: {}, input: {}, revisions: {} });
  const change = (next: HistoryNavigation) => {
    memory?.current.set(key, next);
    setNavigation(next);
  };
  return [navigation, change] as const;
}
