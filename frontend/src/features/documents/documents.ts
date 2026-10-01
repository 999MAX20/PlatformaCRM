// Page bodies intentionally remain empty until the owner supplies lawyer-approved copy.
export const legalDocuments = [
  { id: "terms", titleKey: "documents.terms" },
  { id: "privacy", titleKey: "documents.privacy" },
  { id: "personal-data", titleKey: "documents.personalData" },
  { id: "company-data", titleKey: "documents.companyData" },
] as const;

export const documentPath = (id: string) => `/documents/${id}`;
