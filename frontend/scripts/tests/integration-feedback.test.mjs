import assert from "node:assert/strict";
import test from "node:test";
import { merchantSafeIntegrationError as message } from "../../src/features/integrations/utils.ts";
const t = key => key;

test("disabled integration and safe provider failure keep the real cause for every capability", () => {
  for (const manage of [true, false, undefined]) {
    assert.equal(message("Telegram integration is disabled.", t, manage), "integrations.error.integrationDisabled");
    assert.equal(message("The external provider could not complete the request.", t, manage), "integrations.error.providerUnavailable");
    assert.equal(message("unknown token=private-value", t, manage), "integrations.error.actionRequired");
  }
});
test("setup guidance follows capabilities and distinguishes absent and rejected keys", () => {
  for (const [reason, cause] of [["Telegram bot token is missing.", "credentialsMissing"], ["HTTP Error 401: Unauthorized", "credentialsInvalid"], ["Telegram webhook secret is missing.", "webhookRequired"]]) {
    assert.equal(message(reason, t, true), `integrations.error.${cause}Manage`);
    assert.equal(message(reason, t, false), `integrations.error.${cause}ReadOnly`);
    assert.equal(message(reason, t), `integrations.error.${cause}`);
  }
});
test("CRM request denial stays separate from provider denial and translated errors", () => {
  const error = status => ({ isAxiosError: true, response: { status, data: {} } });
  assert.equal(message(error(403), t, true), "integrations.error.permission");
  assert.equal(message("Provider returned 403 Forbidden", t, true), "integrations.error.providerPermission");
  assert.equal(message(error(401), t, true), "actions.errorUnauthenticated");
  assert.equal(message({ isAxiosError: true }, t, true), "actions.errorNetwork");
  assert.equal(message(error(429), t, true), "actions.errorRateLimited");
});
