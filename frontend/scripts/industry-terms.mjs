// Generic UI labels must not inherit the pilot industry's vocabulary.
// Industry selectors and safety language are distinct from generic entity names.
const explicitIndustryKeys = new Set(["businessType.dentistry", "businessType.medical"]);
const industryEntity = /(?:^|[^\p{L}])(?:клиник[\p{L}]*|пациент[\p{L}]*|врач[\p{L}]*|кресл[\p{L}]*|стоматолог[\p{L}]*|емхана[\p{L}]*|дәрігер[\p{L}]*|орындық[\p{L}]*|clinics?|patients?|doctors?|dentists?|dentistry|dental|chairs?)(?=$|[^\p{L}])/iu;

export function industryTermViolations(entries) {
  return entries
    .filter(([key, value]) => !explicitIndustryKeys.has(key) && industryEntity.test(value))
    .map(([key]) => key);
}
