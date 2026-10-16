import { apiClient } from "./client";
import type { SupportActor, SupportCase, SupportEvent, SupportFilters, SupportIncident, SupportIncidentRef, SupportMessage, SupportNote, SupportPage, SupportScope, SupportStatus } from "../types/support";

const root = (scope: SupportScope) => scope.platform ? "/api/platform/support-cases/" : "/api/support/cases/";
const params = (scope: SupportScope, extra: SupportFilters = {}) => ({ ...extra, ...(!scope.platform ? { business: scope.business } : {}) });
const keyed = (scope: SupportScope, key: string) => ({ params: params(scope), headers: { "Idempotency-Key": key } });

export const supportApi = {
  list: async (scope: SupportScope, filters: SupportFilters) => (await apiClient.get<SupportPage<SupportCase>>(root(scope), { params: params(scope, filters) })).data,
  detail: async (scope: SupportScope, id: number) => (await apiClient.get<SupportCase>(`${root(scope)}${id}/`, { params: params(scope) })).data,
  create: async (scope: SupportScope, payload: { subject: string; text: string; business?: number; incident?: SupportIncidentRef; requester_id?: number }, key: string) => (await apiClient.post<SupportCase>(root(scope), payload, keyed(scope, key))).data,
  incident: async (business: number, incident: SupportIncidentRef, page = 1) => (await apiClient.get<SupportPage<SupportCase> & { incident: SupportIncident }>("/api/platform/support-incidents/", { params: { business, ...incident, page, page_size: 10 } })).data,
  caseIncidents: async (id: number, page = 1) => (await apiClient.get<SupportPage<SupportIncident>>(`/api/platform/support-cases/${id}/incidents/`, { params: { page, page_size: 10 } })).data,
  linkIncident: async (id: number, business: number, incident: SupportIncidentRef) => (await apiClient.post(`/api/platform/support-cases/${id}/incidents/`, { business, ...incident })).data,
  messages: async (scope: SupportScope, id: number, page = 1) => (await apiClient.get<SupportPage<SupportMessage>>(`${root(scope)}${id}/messages/`, { params: params(scope, { page, page_size: 20 }) })).data,
  reply: async (scope: SupportScope, id: number, text: string, key: string) => (await apiClient.post<SupportMessage>(`${root(scope)}${id}/messages/`, { text }, keyed(scope, key))).data,
  notes: async (id: number, page = 1) => (await apiClient.get<SupportPage<SupportNote>>(`/api/platform/support-cases/${id}/internal-notes/`, { params: { page, page_size: 10 } })).data,
  addNote: async (id: number, text: string, key: string) => (await apiClient.post<SupportNote>(`/api/platform/support-cases/${id}/internal-notes/`, { text }, { headers: { "Idempotency-Key": key } })).data,
  events: async (scope: SupportScope, id: number, page = 1) => (await apiClient.get<SupportPage<SupportEvent>>(`${root(scope)}${id}/events/`, { params: params(scope, { page, page_size: 10 }) })).data,
  markRead: async (scope: SupportScope, id: number, throughId: number) => (await apiClient.post<{ through_id: number }>(`${root(scope)}${id}/read/`, { through_id: throughId }, { params: params(scope) })).data,
  assign: async (id: number, assignedTo: number | null, version: number) => (await apiClient.post<SupportCase>(`/api/platform/support-cases/${id}/assign/`, { assigned_to: assignedTo, version })).data,
  transition: async (id: number, status: SupportStatus, reason: string, version: number) => (await apiClient.post<SupportCase>(`/api/platform/support-cases/${id}/transition/`, { status, reason, version })).data,
  reopen: async (scope: SupportScope, id: number, reason: string, version: number) => (await apiClient.post<SupportCase>(`${root(scope)}${id}/reopen/`, { reason, version }, { params: params(scope) })).data,
  staff: async (search = "") => (await apiClient.get<SupportPage<SupportActor>>("/api/platform/support-cases/staff/", { params: { search, page_size: 100 } })).data,
};
