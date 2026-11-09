export function voiceCardContext(pathname: string, search: string): { entity: "clients" | "tasks" | "appointments"; id: number } | undefined {
  const match = /^\/app\/(clients|tasks|appointments|calendar)(?:\/(\d+))?\/?$/.exec(pathname);
  if (!match) return undefined;
  const entity = match[1] === "calendar" ? "appointments" : match[1] as "clients" | "tasks" | "appointments";
  const parameter = { clients: "client", tasks: "task", appointments: "appointment" }[entity];
  const value = match[2] || new URLSearchParams(search).get(parameter) || "";
  const id = Number(value);
  return /^\d+$/.test(value) && Number.isSafeInteger(id) && id > 0 ? { entity, id } : undefined;
}

export function voiceBranchContext(pathname: string, search: string): number | undefined {
  if (!/^\/app\/(calendar|appointments)\/?$/.test(pathname)) return undefined;
  const value = new URLSearchParams(search).get("branch") || "";
  const id = Number(value);
  return /^\d+$/.test(value) && Number.isSafeInteger(id) && id > 0 ? id : undefined;
}
