import assert from "node:assert/strict";
import test from "node:test";
import { industryTermViolations } from "../industry-terms.mjs";

test("rejects industry entity labels in each supported locale, including inflections", () => {
  for (const value of ["Работа клиники", "Пациенты", "Выберите врача", "Кресло 1", "Администратор стоматологии", "Clinic work", "PATIENT", "Dental receptionist", "Chair 1", "Клиниканың жұмысы", "Дәрігерді таңдаңыз", "Орындық 1"]) {
    assert.deepEqual(industryTermViolations([["newPage.label", value]]), ["newPage.label"], value);
  }
});

test("checks visible values, preserving technical keys and neutral words", () => {
  assert.deepEqual(industryTermViolations([
    ["clinicCrm.tab.work", "Работа бизнеса"], ["settings.role.doctor", "Специалист"],
    ["supportCases.status.waiting_clinic", "Waiting for business"], ["newPage.label", "Recipient status"],
  ]), []);
});

test("allows explicit industry choices without exempting unrelated generic labels", () => {
  assert.deepEqual(industryTermViolations([
    ["businessType.dentistry", "Стоматология"], ["businessType.medical", "Medical"],
    ["businessType.title", "Clinic"],
  ]), ["businessType.title"]);
});

test("preserves medical and legal safety restrictions", () => {
  assert.deepEqual(industryTermViolations([
    ["aiSetup.dentalPrompt", "Не ставь диагнозы и не назначай лечение."],
    ["aiSetup.dentalEscalation", "Escalate clinical questions to the administrator."],
    ["aiAgents.defaultEscalation", "Медицинский или юридический вопрос"],
  ]), []);
});
