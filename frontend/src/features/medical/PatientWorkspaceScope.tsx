import { createContext, useCallback, useContext, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";
import { TerminologyProvider } from "../../lib/i18n";
import { patientRoute, patientTemplate } from "./patientTerminology";

const DentalWorkspaceContext = createContext(false);
const neutralTemplate = (_key: string, template: string) => template;

export function usePatientRoute() {
  const dental = useContext(DentalWorkspaceContext);
  return useCallback((path: string) => patientRoute(path, dental), [dental]);
}

export function PatientWorkspaceScope({ children }: { children: ReactNode }) {
  const { business, isLoading } = useActiveBusiness();
  const { user } = useAuth();
  const location = useLocation();
  const capability = user?.capabilities?.[String(business?.id)];
  const dental = capability?.business_type === "dentistry";
  const path = patientRoute(location.pathname, dental);
  if (!isLoading && path !== location.pathname) {
    return <Navigate replace to={`${path}${location.search}${location.hash}`} state={location.state} />;
  }
  return <DentalWorkspaceContext.Provider value={dental}>
    <TerminologyProvider transform={dental ? patientTemplate : neutralTemplate}>{children}</TerminologyProvider>
  </DentalWorkspaceContext.Provider>;
}
