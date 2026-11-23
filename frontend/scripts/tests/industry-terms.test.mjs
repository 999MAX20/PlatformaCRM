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

test("allows patient labels only in the explicit medical module keys", () => {
  assert.deepEqual(industryTermViolations([
    ["medical.fullName", "Patient full name"], ["medical.create", "Создать профиль пациента"],
    ["medical.clinical.verifyFirst", "Verify the patient’s identity"],
    ["medical.tooth.title", "Dental chart"], ["medical.tooth.orientation", "Sides relative to the patient"],
    ["medical.participation.invite", "Пригласить врача"], ["medical.participation.doctor", "Дәрігер"],
    ["medical.participation.workDirectionHint", "Врач увидит это до принятия приглашения."],
    ["medical.roles.kind.doctor", "Врач"], ["medical.roles.resource.medical_patients", "Пациенты"],
    ["medical.templates.draftStatus", "Клиникалық қолдану үшін бекітілмеген."],
    ["medical.search.title", "Поиск пациента"], ["medical.search.empty", "No patients found"],
    ["medical.fields.clinicName", "Clinic name"], ["medical.fields.clinicLegalName", "Юридическое название клиники"],
    ["medical.fields.clinicTaxId", "Clinic tax ID"], ["medical.fields.clinicAddress", "Адрес клиники"],
    ["medical.fields.clinicPhone", "Клиника телефоны"], ["medical.fields.doctorName", "Doctor full name"],
    ["medical.documents.reviewed", "Проверено врачом"],
    ["medical.documents.reviewConfirmed", "Мазмұнды дәрігер растады"],
    ["medical.assistants.saved", "Черновик сохранён для проверки врачом."],
    ["medical.assistants.waitingEncounter", "Дәрігер жазбаны әлі ашқан жоқ."],
    ["medical.assistants.noApprovedSource", "Обратитесь к врачу приёма."],
    ["medical.reception.notBooking", "Reception will agree a time with the patient."],
    ["medical.reception.onsite", "Пациент сейчас в клинике"],
    ["medical.reception.state.booked", "Пациент жазылды"],
    ["medical.reception.state.declined", "Patient declined"],
    ["clients.create", "Создать пациента"], ["medical.unreviewed", "Doctor"],
  ]), ["clients.create", "medical.unreviewed"]);
});
