package kz.zani.mobile

import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant
import java.time.ZoneId

class AgendaContractTest {
    private fun fixture(name: String): String = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun loaded(): AgendaSession = AgendaSession().apply { install(JsonContracts.bootstrap(fixture("bootstrap"))) }
    private fun failure(expected: ReadProblem, block: () -> Unit) {
        try { block(); fail("Expected $expected") } catch (error: ReadException) { assertEquals(expected, error.problem) }
    }
    @Test fun bootstrapAndSharedIdentity() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        assertTrue(session.receive(JsonContracts.appointments(fixture("appointments-101")), scope))
        assertEquals(listOf(501, 502), session.items.map { it.id })
        assertTrue(session.receive(JsonContracts.detail(fixture("appointment-101-501")), session.beginDetail(501)))
        assertEquals(session.items.first().id, session.detail!!.appointment.id)
    }
    @Test fun freshDetailUpdatesSameIdentityAndRedaction() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-101")), scope)
        val detail = JsonContracts.detail(fixture("appointment-101-501"))
        session.receive(detail.copy(appointment = detail.appointment.copy(title = null, status = "future_status")), session.beginDetail(501))
        assertNull(session.items.first().title)
        assertEquals("future_status", session.items.first().status)
    }
    @Test fun contextSwitchRejectsLateAndForeignResponses() {
        val session = loaded(); val first = session.begin(101, "2026-10-28")
        val second = session.begin(202, "2026-10-28")
        val old = JsonContracts.appointments(fixture("appointments-101"))
        assertFalse(session.receive(old, first)); assertTrue(session.items.isEmpty()); assertNull(session.detail)
        failure(ReadProblem.INVALID_PAYLOAD) { session.receive(old, second) }
        session.receive(JsonContracts.appointments(fixture("appointments-202")), second)
        assertEquals(listOf(601), session.items.map { it.id })
    }
    @Test fun sameIdRetryRejectsOlderDetailAndPreservesRedaction() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-101")), scope)
        val detail = JsonContracts.detail(fixture("appointment-101-501"))
        val first = session.beginDetail(501); val retry = session.beginDetail(501)
        assertNotEquals(first, retry); assertNotEquals(first, session.detailSelection)
        assertTrue(session.receive(detail.copy(appointment = detail.appointment.copy(title = null)), retry))
        assertFalse(session.receive(detail, first)); assertNull(session.items.first().title)
    }
    @Test fun backAndReopenRejectPreviousVisitResponse() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-101")), scope)
        val detail = JsonContracts.detail(fixture("appointment-101-501")); val first = session.beginDetail(501)
        session.clearDetail()
        assertNull(session.detailSelection); assertFalse(session.receive(detail, first)); assertNull(session.detail)
        val reopened = session.beginDetail(501)
        assertFalse(session.receive(detail, first)); assertTrue(session.receive(detail, reopened))
    }
    @Test fun contextChangeInvalidatesDetailAndUnknownIdCannotStart() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-101")), scope)
        failure(ReadProblem.INVALID_CONTEXT) { session.beginDetail(999) }
        val request = session.beginDetail(501)
        session.begin(202, "2026-10-28")
        assertNull(session.detailSelection)
        assertFalse(session.receive(JsonContracts.detail(fixture("appointment-101-501")), request))
    }
    @Test fun activeBusinessTimezoneMustMatchMembershipWithoutErasingState() {
        val bootstrap = JsonContracts.bootstrap(fixture("bootstrap"))
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-101")), scope)
        for (timezone in listOf("UTC", "Invalid/Zone")) {
            failure(ReadProblem.INVALID_PAYLOAD) { session.install(bootstrap.copy(activeBusiness = bootstrap.activeBusiness.copy(timezone = timezone))) }
            assertEquals(scope, session.selection); assertEquals(listOf(501, 502), session.items.map { it.id })
        }
    }
    @Test fun membershipAndInvalidDayAreRejected() {
        val session = loaded()
        failure(ReadProblem.INVALID_CONTEXT) { session.begin(303, "2026-10-28") }
        failure(ReadProblem.INVALID_CONTEXT) { session.begin(101, "2026-02-30") }
    }
    @Test fun nullableResourceAndPartialResultStayExplicit() {
        assertNull(JsonContracts.detail(fixture("appointment-101-502")).resource!!.id)
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        session.receive(JsonContracts.appointments(fixture("appointments-partial")), scope)
        assertTrue(session.isPartial); assertEquals(1, session.items.size)
    }
    @Test fun duplicateIdsRejectButUncertainTimesRemainExplicit() {
        val session = loaded(); val scope = session.begin(101, "2026-10-28")
        val list = JsonContracts.appointments(fixture("appointments-101"))
        failure(ReadProblem.INVALID_PAYLOAD) { session.receive(list.copy(items = listOf(list.items[0], list.items[0])), scope) }
        assertTrue(session.receive(list.copy(items = listOf(list.items[0].copy(endAt = list.items[0].startAt))), scope))
        assertEquals(1,AgendaDayDisplay(session.items,scope.day,session.responseDay,scope.business.timezone).uncertain.size)
    }
    @Test fun businessTimezoneBoundary() {
        assertEquals("2026-10-28", Instant.parse("2026-10-27T20:00:00Z").atZone(ZoneId.of("Asia/Almaty")).toLocalDate().toString())
    }
    @Test fun readRequestContract() = runBlocking {
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { request ->
            requests += request
            ReadResponse(200, fixture(when (request.path) {
                "/api/mobile/v1/bootstrap/" -> "bootstrap"
                "/api/mobile/v1/appointments/" -> "appointments-101"
                else -> "appointment-101-501"
            }))
        })
        repo.bootstrap(); repo.appointments(101, "2026-10-28"); repo.appointment(101, 501)
        assertEquals(ReadRequest("/api/mobile/v1/bootstrap/"), requests[0])
        assertEquals(ReadRequest("/api/mobile/v1/appointments/", mapOf("business" to "101", "date" to "2026-10-28", "limit" to "50")), requests[1])
        assertEquals(ReadRequest("/api/mobile/v1/appointments/501/", mapOf("business" to "101")), requests[2])
    }
    @Test fun errorKindsAndMalformedPayload() = runBlocking {
        for ((status, expected) in listOf(403 to ReadProblem.DENIED, 404 to ReadProblem.NOT_FOUND, 503 to ReadProblem.UNAVAILABLE)) {
            val repo = APIReadRepository(ReadTransport { ReadResponse(status, "") })
            try { repo.bootstrap(); fail("Expected $expected") } catch (error: ReadException) { assertEquals(expected, error.problem) }
        }
        failure(ReadProblem.INVALID_PAYLOAD) { JsonContracts.bootstrap("{}") }
    }
}
