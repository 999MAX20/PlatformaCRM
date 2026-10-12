import { appointmentsApi } from "./appointments";
import { botConversationsApi } from "./bots";
import { clientsApi } from "./clients";
import { dealsApi } from "./deals";
import { leadsApi } from "./leads";
import { resourcesApi } from "./resources";
import { tasksApi } from "./tasks";
import type { Id } from "../types";

export type TaskRelationType = "client" | "lead" | "deal" | "appointment" | "conversation" | "parent_task" | "specialist";
export async function taskRelationOptions(type: TaskRelationType, business: Id, search: string, taskId?: Id) {
  const params = { business, search, page_size: 30 };
  let rows: { id: Id; business: Id; label: string }[];
  switch (type) {
    case "client": rows = (await clientsApi.list(params)).map(v => ({ ...v, label: v.full_name })); break;
    case "lead": rows = (await leadsApi.list(params)).map(v => ({ ...v, label: v.client_name || v.message || `#${v.id}` })); break;
    case "deal": rows = (await dealsApi.list(params)).map(v => ({ ...v, label: v.title })); break;
    case "appointment": rows = (await appointmentsApi.list(params)).map(v => ({ ...v, label: [v.client_name, v.service_name, v.start_at].filter(Boolean).join(" · ") })); break;
    case "conversation": rows = (await botConversationsApi.list(params)).map(v => ({ ...v, label: v.client_name || v.external_user_id || `#${v.id}` })); break;
    case "specialist": rows = (await resourcesApi.list({ ...params, status: "active" })).map(v => ({ ...v, label: v.name })); break;
    case "parent_task": rows = (await tasksApi.list(params)).filter(v => v.id !== taskId).map(v => ({ ...v, label: v.title })); break;
  }
  return rows.filter(v => String(v.business) === String(business)).map(v => ({ value: String(v.id), label: v.label }));
}
