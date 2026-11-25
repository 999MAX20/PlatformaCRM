// Only CRM person terminology belongs here. Provider/API clients and public copy stay neutral.
const patientNamespaces = new Set([
  "clients", "client", "appointments", "appointment", "calendar", "records", "crm",
  "plans", "planMoney", "planCorrection", "medical", "forms", "validation", "crmCard",
  "search", "command", "leads", "deals", "payments", "tasks", "timeline", "inbox",
  "leadForm", "clinicCrm", "taskWorkspace", "planClosure", "finance",
]);
const patientKeys = new Set(["nav.clients", "nav.group.clients", "nav.group.dailyHint", "common.client", "header.search"]);

export function patientTemplate(key: string, template: string): string {
  if (!patientNamespaces.has(key.split(".")[0]) && !patientKeys.has(key)) return template;
  // Interpolation happens afterwards: names, notes, and other user data are never rewritten.
  return template.split(/(\{[^}]+\})/g).map(part => {
    if (part.startsWith("{")) return part;
    return part
      .replace(/Клиентская база/g, "База пациентов")
      .replace(/клиентская база/g, "база пациентов")
      .replace(/(?<!\p{L})клиент/giu, word => word[0] === "К" ? "Пациент" : "пациент")
      .replace(/\b(clients?|customers?)\b/gi, word => {
        const plural = word.toLowerCase().endsWith("s");
        const noun = plural ? "patients" : "patient";
        return word[0] === word[0].toUpperCase() ? noun[0].toUpperCase() + noun.slice(1) : noun;
      });
  }).join("");
}

export function patientRoute(path: string, dental: boolean): string {
  const source = dental ? "clients" : "patients";
  const target = dental ? "patients" : "clients";
  return path.replace(new RegExp(`^/app/${source}(?=/|\\?|#|$)`), `/app/${target}`);
}
