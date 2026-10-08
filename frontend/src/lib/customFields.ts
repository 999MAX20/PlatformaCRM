import type { CustomFieldDefinition } from "../types";

export function customFieldOptions(definition: Pick<CustomFieldDefinition, "options_json">) {
  return (definition.options_json?.options || []).map((option) => {
    if (typeof option === "string") return { value: option, label: option };
    const value = String(option.value ?? option.key ?? option.label ?? "");
    return { value, label: String(option.label ?? value) };
  }).filter((option) => option.value);
}
