type Review = { timezone: string; values: Record<string, string | null>; before: Record<string, string | null> };

export function reviewValue(field: string, value: unknown, side: "values" | "before", review: Review | undefined, language: string, unavailable: string): string {
  if (value === null || value === undefined || value === "") return "—";
  if (review && Object.prototype.hasOwnProperty.call(review[side], field)) return review[side][field] || unavailable;
  if (field.endsWith("_at") && typeof value === "string" && Number.isFinite(Date.parse(value))) {
    try {
      return new Intl.DateTimeFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-RU" : "en-GB", {
        day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: review?.timezone || "UTC",
      }).format(new Date(value));
    } catch { return value; }
  }
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
