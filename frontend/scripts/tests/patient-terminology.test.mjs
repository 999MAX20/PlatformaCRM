import assert from "node:assert/strict";
import test from "node:test";
import { patientRoute, patientTemplate } from "../../src/features/medical/patientTerminology.ts";
import { recordReturnPath } from "../../src/features/calendar/recordFilters.ts";
import { clients as ru } from "../../src/lib/i18n/ru/clients.ts";
import { clients as kk } from "../../src/lib/i18n/kk/clients.ts";
import { clients as en } from "../../src/lib/i18n/en/clients.ts";
import { calendar as calendarRu } from "../../src/lib/i18n/ru/calendar.ts";
import { calendar as calendarKk } from "../../src/lib/i18n/kk/calendar.ts";
import { calendar as calendarEn } from "../../src/lib/i18n/en/calendar.ts";

test("dental routes preserve IDs, query, hash; core routes remain neutral", () => {
  for (const suffix of ["", "/164", "?page=2&search=test", "/164?tab=files#entry"]) {
    assert.equal(patientRoute(`/app/clients${suffix}`, true), `/app/patients${suffix}`);
    assert.equal(patientRoute(`/app/patients${suffix}`, false), `/app/clients${suffix}`);
    assert.equal(patientRoute(`/app/clients${suffix}`, false), `/app/clients${suffix}`);
    assert.equal(patientRoute(`/app/patients${suffix}`, true), `/app/patients${suffix}`);
  }
});

test("routing does not rewrite external URLs, nested strings or similarly named routes", () => {
  for (const path of ["https://example.test/app/clients", "//example.test/app/clients", "/app/clients-export", "/api/clients/", "/app/appointments?return=/app/clients"]) {
    assert.equal(patientRoute(path, true), path);
  }
});

test("appointment return accepts patient pages but rejects external/unsafe paths", () => {
  assert.equal(recordReturnPath("/app/patients/164?tab=visits"), "/app/patients/164?tab=visits");
  for (const value of ["//evil.test", "/app/patients-other", "/app/patients/1\n", "/app/patients/1/../../settings"]) {
    assert.equal(recordReturnPath(value), "/app/appointments");
  }
});

test("patient labels retain grammatical endings and placeholders in RU/KK/EN", () => {
  assert.equal(patientTemplate("clients.pageBack", "Назад к клиентам"), "Назад к пациентам");
  assert.equal(patientTemplate("clients.title", "Клиенттер"), "Пациенттер");
  assert.equal(patientTemplate("clients.title", "Clients"), "Patients");
  assert.equal(patientTemplate("clients.notice", "Клиент {client_name}: {count} клиентов"), "Пациент {client_name}: {count} пациентов");
  assert.equal(patientTemplate("clients.baseTitle", "Клиентская база"), "База пациентов");
});

test("technical and public terminology stays unchanged", () => {
  assert.equal(patientTemplate("integrations.oauthClient", "Client ID"), "Client ID");
  assert.equal(patientTemplate("signup.client", "Клиент"), "Клиент");
  assert.equal(patientTemplate("platform.client", "Client"), "Client");
});

test("all client dictionary templates are adapted without mutating core dictionaries", () => {
  for (const dictionary of [ru, kk, en, calendarRu, calendarKk, calendarEn]) {
    const original = JSON.stringify(dictionary);
    for (const [key, value] of Object.entries(dictionary)) {
      const result = patientTemplate(key, value);
      assert.doesNotMatch(result, /клиент|\bclients?\b|\bcustomers?\b/iu, key);
      assert.deepEqual(result.match(/\{[^}]+\}/g), value.match(/\{[^}]+\}/g), key);
    }
    assert.equal(JSON.stringify(dictionary), original);
  }
});
