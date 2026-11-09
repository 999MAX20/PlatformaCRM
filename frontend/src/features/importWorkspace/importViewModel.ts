export const displayImportValue = (value: unknown): string => value === null || value === undefined || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);

export function describeImportErrors(errors: unknown, t: (key: string) => string): string {
  const messages: string[] = [];
  const visit = (value: unknown, field = "") => {
    if (Array.isArray(value)) { value.forEach(item => visit(item, field)); return; }
    if (value && typeof value === "object") { Object.entries(value).forEach(([key, item]) => visit(item, key)); return; }
    const detail = String(value || "").toLowerCase();
    let key = "reviewRow";
    if (/duplicate|possible match|more than once|not unique/.test(detail + field)) key = "duplicate";
    else if (/overlap|already booked|conflict|busy/.test(detail + field)) key = "conflict";
    else if (/working hours|outside.*hours|schedule|closed/.test(detail)) key = "schedule";
    else if (/permission|permitted scope|not available|active membership/.test(detail)) key = "access";
    else if (/source-row|reference|identifier|linked/.test(detail) || /_ref$/.test(field)) key = "reference";
    else if (/required|blank|provide a name/.test(detail)) key = "required";
    else if (field === "email" || /email/.test(detail)) key = "email";
    else if (/date|time|timezone/.test(detail) || field === "start_at") key = "date";
    else if (/number|decimal|integer|greater|less than|digits/.test(detail)) key = "number";
    else if (/boolean|option|choice|status/.test(detail) || field === "status") key = "choice";
    const translatedField = t(`importWorkspace.field.${field}`);
    const prefix = translatedField !== `importWorkspace.field.${field}` ? `${translatedField}: ` : "";
    messages.push(prefix + t(`importWorkspace.validation.${key}`));
  };
  visit(errors);
  return [...new Set(messages)].join(" ");
}
