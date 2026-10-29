export function captureFieldOptions(metadata: Record<string, unknown> = {}) {
  const options = Array.isArray(metadata.options) ? metadata.options : [];
  return options.map((option: unknown) => {
    if (typeof option === "string") return { value: option, original: option };
    if (!option || typeof option !== "object") return { value: "", original: option };
    const item = option as Record<string, unknown>;
    return { value: String(item.value ?? item.key ?? item.label ?? ""), original: item };
  }).filter(option => option.value);
}

export function captureOptionsPatch(metadata: Record<string, unknown> | undefined, values: string[]) {
  const original = captureFieldOptions(metadata);
  if (JSON.stringify(values) === JSON.stringify(original.map(option => option.value))) return undefined;
  return { ...metadata, options: values.map(value => original.find(option => option.value === value)?.original ?? value) };
}
