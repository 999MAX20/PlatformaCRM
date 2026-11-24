import { createContext } from "react";

export const ClinicalPageSlots = createContext<{
  save: HTMLElement | null;
  completion: HTMLElement | null;
} | null>(null);
