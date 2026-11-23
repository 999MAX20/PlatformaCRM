import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import type { ClinicalReadScope } from "../../api/medicalClinical";
import { historyScopeKey } from "./clinicalHistoryNavigation";

type ToothNavigation = { date: string; asOf?: string; mode: string; quadrant: number; focusedTooth?: number };
type PlanNavigation = { archived: boolean; cursor?: number };
type ViewMemory = { teeth: Map<string, ToothNavigation>; plans: Map<string, PlanNavigation> };
const ViewContext = createContext<ViewMemory | null>(null);

export function ClinicalViewNavigationProvider({ children }: { children: ReactNode }) {
  const memory = useRef<ViewMemory>({ teeth: new Map(), plans: new Map() });
  return <ViewContext.Provider value={memory.current}>{children}</ViewContext.Provider>;
}

function useNavigation<T>(scope: ClinicalReadScope, memory: Map<string, T> | undefined, initial: T) {
  const key = historyScopeKey(scope);
  const [navigation, setNavigation] = useState(() => memory?.get(key) ?? initial);
  const change = (next: T) => {
    memory?.set(key, next);
    setNavigation(next);
  };
  return [navigation, change] as const;
}

export function useToothNavigation(scope: ClinicalReadScope) {
  return useNavigation<ToothNavigation>(scope, useContext(ViewContext)?.teeth,
    { date: "", mode: "permanent", quadrant: 1 });
}

export function usePlanNavigation(scope: ClinicalReadScope) {
  return useNavigation<PlanNavigation>(scope, useContext(ViewContext)?.plans, { archived: false });
}
