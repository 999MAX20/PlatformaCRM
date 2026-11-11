import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { timeline as ru } from "../../src/lib/i18n/ru/timeline.ts";
import { timeline as kk } from "../../src/lib/i18n/kk/timeline.ts";
import { timeline as en } from "../../src/lib/i18n/en/timeline.ts";
import {
  readTimelineFilters,
  safeTimelineMetadata,
  timelineDate,
  timelineDetailTransitions,
  timelineSummary,
  timelineEntityRoutes,
  timelineObjectLabel,
} from "../../src/features/timeline/timelinePresentation.ts";

test("URL filters retain search and normalize invalid pagination", () => {
  const filters = readTimelineFilters(
    new URLSearchParams(
      "search=Alice&category=task&actor=12&page=-5&page_size=999",
    ),
  );
  assert.deepEqual(filters, {
    entity_type: "",
    entity_id: "",
    search: "Alice",
    category: "task",
    actor: "12",
    date_from: "",
    date_to: "",
    page: 1,
    page_size: 20,
  });
  assert.equal(
    readTimelineFilters(new URLSearchParams("page=3&page_size=50")).page,
    3,
  );
});

test("every domain event has an explicit label in RU/KK/EN, including historical aliases", () => {
  const source = readFileSync(new URL("../../../apps/activities/taxonomy.py", import.meta.url), "utf8").split("EVENT_ALIASES")[0];
  const events = [...source.matchAll(/^    [A-Z_]+ = "([a-z_]+)"/gm)].map(match => match[1]);
  assert.ok(events.length > 50);
  for (const dictionary of [ru, kk, en]) {
    const t = key => dictionary[key] || key;
    for (const event of events) assert.ok(dictionary[`timeline.eventType.${event}`], event);
    assert.equal(timelineSummary("client.archived", t), dictionary["timeline.eventType.client_archived"]);
    assert.equal(timelineSummary("bot.deleted", t), dictionary["timeline.eventType.bot_deleted"]);
    assert.equal(timelineSummary("deal_marked_lost", t), dictionary["timeline.eventType.deal_lost"]);
  }
});

test("legacy appointment metadata yields a status change without leaking a reason", () => {
  const t = key => ({"status.confirmed":"Confirmed","status.no_show":"No show"})[key] || key;
  const details = timelineDetailTransitions({from:"confirmed",to:"no_show",reason:"PRIVATE",fields:{phone:"PRIVATE",token:"PRIVATE"}}, "en", "UTC", key => en[key] || t(key));
  assert.equal(details[0].value,"Confirmed → No show");
  assert.doesNotMatch(JSON.stringify(details),/PRIVATE|token/);
  assert.match(JSON.stringify(details),/Phone/);
});

test("partial history never invents an old value and denied objects never reveal their name", () => {
  const t = key => en[key] || key;
  const details = timelineDetailTransitions({start_at:"2026-11-11T10:00:00Z"},"en","UTC",t);
  assert.doesNotMatch(details[0].value,/→/);
  assert.equal(timelineObjectLabel({entity_type:"Task",entity_id:"42",entity_name:"Private",entity_available:false},t),en["timeline.objectUnavailable"]);
  assert.equal(timelineObjectLabel({entity_type:"Task",entity_id:"42",entity_name:"Call supplier",entity_available:true},t),"Call supplier");
});

test("historical drilldown retains entity scope and record events open the canonical card", () => {
  const filters = readTimelineFilters(new URLSearchParams("entity_type=Lead&entity_id=42&page=2"));
  assert.equal(filters.entity_type, "Lead");
  assert.equal(filters.entity_id, "42");
  assert.equal(filters.page, 2);
  assert.equal(timelineEntityRoutes.appointment.path, "appointments");
  assert.equal(timelineEntityRoutes.appointment.permission, "appointments");
  assert.equal(timelineEntityRoutes.lead.path, "leads");
});

test("metadata allowlist drops raw payloads, IDs, free text and non-finite values", () => {
  assert.deepEqual(
    safeTimelineMetadata({
      reason: "secret",
      source: "secret",
      token: "secret",
      entity_id: "123",
      provider: { secret: "value" },
      amount_before: Infinity,
      amount_after: "5000.00",
      from_status: "secret",
      to_status: "done",
      start_at: "2026-09-13T19:30:00Z",
      previous_start_at: "secret",
    }),
    {
      amount_after: "5000.00",
      start_at: "2026-09-13T19:30:00Z",
      to_status: "done",
    },
  );
});

test("business timezone is used consistently for day and clock", () => {
  assert.doesNotMatch(timelineDate("2026-09-13T19:30:00Z", "kk", "Asia/Almaty"), /M09/);
  assert.match(
    timelineDate("2026-09-13T19:30:00Z", "en", "Asia/Almaty"),
    /14 September 2026/,
  );
  assert.equal(
    timelineDate("2026-09-13T19:30:00Z", "en", "Asia/Almaty", true),
    "00:30",
  );
  assert.equal(timelineDate("invalid", "ru", "UTC"), "—");
  assert.doesNotThrow(() =>
    timelineDate("2026-09-13T19:30:00Z", "kk", "Invalid/Zone"),
  );
});

test("unknown event text cannot become merchant copy", () => {
  const t = (key) =>
    ({
      "timeline.otherEvent": "Event",
      "crmCard.timelineEvent.task_created": "Task created",
    })[key] || key;
  assert.equal(timelineSummary("provider_secret", t), "Event");
  assert.equal(timelineSummary("task_created", t), "Task created");
});

test("detail transitions localize status and business dates without technical fields", () => {
  const t = (key) =>
    ({ "status.new": "Новая", "status.done": "Готово" })[key] || key;
  const result = timelineDetailTransitions(
    {
      from_status: "new",
      to_status: "done",
      start_at: "2026-09-13T19:30:00Z",
      source: "secret",
    },
    "ru",
    "Asia/Almaty",
    t,
  );
  assert.equal(result[0].value, "Новая → Готово");
  assert.match(result[1].value, /14 сентября 2026.*00:30/);
  assert.doesNotMatch(JSON.stringify(result), /secret/);
  assert.equal(timelineEntityRoutes.connector, undefined);
});
