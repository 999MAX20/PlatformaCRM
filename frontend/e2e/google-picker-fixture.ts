let failed = false;
export async function chooseGoogleSpreadsheet() {
  const scenario = new URLSearchParams(location.search).get("google_fixture");
  if (scenario === "cancel") return null;
  if (scenario === "error_once" && !failed) { failed = true; return "bad"; }
  return "isolated_google_sheet";
}
