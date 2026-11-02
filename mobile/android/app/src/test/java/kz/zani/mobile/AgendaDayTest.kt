package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.time.ZoneId

@OptIn(ExperimentalCoroutinesApi::class)
class AgendaDayTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun edge() = JsonContracts.appointments(fixture("appointments-agenda-edge-101"))
    private fun display(p: AppointmentList = edge(), day: String = "2026-10-29", zone: String = "Asia/Almaty") = AgendaDayDisplay(p.items,day,p.date,zone)
    private class Controlled(val bootstrap: Bootstrap) : AgendaRepository {
        val pages=mutableListOf<CompletableDeferred<AppointmentList>>()
        val details=mutableListOf<CompletableDeferred<AppointmentDetail>>()
        override suspend fun bootstrap()=bootstrap
        override suspend fun appointments(business: Int, day: String)=CompletableDeferred<AppointmentList>().also { pages+=it }.await()
        override suspend fun appointment(business: Int, id: Int)=CompletableDeferred<AppointmentDetail>().also { details+=it }.await()
    }
    private fun check(block: suspend TestScope.(AgendaViewModel,Controlled) -> Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val source=Controlled(JsonContracts.bootstrap(fixture("bootstrap"))); val model=AgendaViewModel(source,initialDay={"2026-10-29"})
        try { block(model,source) } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun dayDisplayRetainsEveryIdentityAndSeparatesUnknownTimesFromScheduledIntervals() {
        val p=edge(); val d=display(); assertEquals(listOf(5602,5601,5603,5604,5605,5606),d.sourceRows.map { it.appointment.id })
        assertEquals(listOf(5601,5602),d.scheduled.map { it.appointment.id })
        assertEquals(listOf(AgendaTimeIssue.UNKNOWN,AgendaTimeIssue.UNKNOWN,AgendaTimeIssue.INVALID_RANGE,AgendaTimeIssue.OTHER_DAY),d.uncertain.map { it.issue })
        assertEquals(p.items.size,d.scheduled.size+d.uncertain.size); assertEquals("not-an-instant",p.items[3].startAt); assertNull(p.items[2].startAt)
        assertTrue(p.isPartial)
    }
    @Test fun missingOrNullTimesAreNotCoercedAndOtherReadTargetsStillRejectUnknownIntervals() {
        val j=JSONObject(fixture("appointment-101-5603")); j.getJSONObject("appointment").remove("start_at")
        val detail=JsonContracts.detail(j.toString()); assertNull(detail.appointment.startAt); assertNull(detail.appointment.endAt)
        assertFalse(AttentionDetail.AppointmentRead(detail).validFor(101,AttentionTarget(AttentionKind.APPOINTMENT,5603)))
        val home=JsonContracts.today(fixture("today-101")); assertFalse(home.copy(appointments=home.appointments!!.copy(items=listOf(detail.appointment))).validFor(101,home.date))
        j.getJSONObject("appointment").put("start_at",42)
        try { JsonContracts.detail(j.toString()); fail() } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem) }
    }
    @Test fun overnightUsesActualEndDateWithoutClippingOrInventingDuration() {
        val row=display().scheduled.last(); assertEquals(5602,row.appointment.id)
        assertEquals("2026-10-29",row.appointment.start.atZone(ZoneId.of("Asia/Almaty")).toLocalDate().toString())
        assertEquals("2026-10-30",row.appointment.end.atZone(ZoneId.of("Asia/Almaty")).toLocalDate().toString())
        assertNull(row.issue)
        assertTrue(formatAgendaEndpoint(row.appointment.endAt,"Asia/Almaty","en")!!.contains("UTC+05:00"))
    }
    @Test fun repeatedDstHourOrdersByInstantAndOffsetsDisambiguateWallClock() {
        val p=JsonContracts.appointments(fixture("appointments-agenda-dst-101")); val d=display(p,"2026-11-01","America/New_York")
        assertEquals(listOf(5612,5611),d.sourceRows.map { it.appointment.id }); assertEquals(listOf(5611,5612),d.scheduled.map { it.appointment.id }); assertTrue(d.uncertain.isEmpty())
        for (language in listOf("ru","kk","en")) {
            val a=d.scheduled[0].appointment; val b=d.scheduled[1].appointment
            assertTrue(formatAgendaEndpoint(a.startAt,"America/New_York",language)!!.contains("UTC-04:00"))
            assertTrue(formatAgendaEndpoint(a.endAt,"America/New_York",language)!!.contains("UTC-05:00"))
            assertNotEquals(formatAgendaEndpoint(a.startAt,"America/New_York",language),formatAgendaEndpoint(b.startAt,"America/New_York",language))
        }
    }
    @Test fun springForwardAndUnknownTimezoneDoNotBecomeFakeFreeTime() {
        val a=edge().items[0].copy(startAt="2026-03-08T06:30:00Z",endAt="2026-03-08T07:30:00Z")
        assertEquals(1,AgendaDayDisplay(listOf(a),"2026-03-08","2026-03-08","America/New_York").scheduled.size)
        assertTrue(formatAgendaEndpoint(a.startAt,"America/New_York","en")!!.contains("UTC-05:00")); assertTrue(formatAgendaEndpoint(a.endAt,"America/New_York","en")!!.contains("UTC-04:00"))
        assertEquals(AgendaTimeIssue.UNKNOWN,AgendaDayDisplay(listOf(a),"2026-03-08","2026-03-08","Invalid/Zone").uncertain[0].issue)
        assertNull(formatAgendaEndpoint(a.startAt,"Invalid/Zone","ru")); assertNull(formatAgendaEndpoint(null,"UTC","kk"))
    }
    @Test fun responseDayMismatchRetainsRowsButNeverPlacesThemOnSelectedDay() {
        val p=edge().copy(date="2026-10-28"); val d=display(p)
        assertTrue(d.scheduled.isEmpty()); assertEquals(6,d.uncertain.size); assertTrue(d.uncertain.all { it.issue==AgendaTimeIssue.SOURCE_DAY })
        val session=AgendaSession(); session.install(JsonContracts.bootstrap(fixture("bootstrap"))); val scope=session.begin(101,"2026-10-29")
        assertTrue(session.receive(p,scope)); assertTrue(session.sourceDayMismatch); assertEquals("2026-10-28",session.responseDay); assertEquals(scope,session.selection)
    }
    @Test fun realDayReadAndEveryIndependentDetailBackKeepsModeDayAndRawUncertainty()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport { request -> requests+=request; ReadResponse(200,fixture(when(request.path) { "/api/mobile/v1/bootstrap/"->"bootstrap"; "/api/mobile/v1/appointments/"->"appointments-agenda-edge-101"; else->"appointment-101-${request.path.trimEnd('/').substringAfterLast('/')}" })) })
        val model=AgendaViewModel(repo,initialDay={"2026-10-29"})
        try {
            model.start(); runCurrent(); model.setMode(AgendaMode.CALENDAR); val ids=model.state.items.map { it.id }
            for (id in ids) { model.detail(id); runCurrent(); assertEquals(id,model.state.detail!!.appointment.id); model.back(); assertEquals(AgendaMode.CALENDAR,model.state.mode); assertEquals("2026-10-29",model.state.selection!!.day); assertEquals(ids,model.state.items.map { it.id }) }
            assertNull(model.state.items.first { it.id==5603 }.startAt); assertEquals("not-an-instant",model.state.items.first { it.id==5604 }.startAt)
            assertEquals(ReadRequest("/api/mobile/v1/appointments/",mapOf("business" to "101","date" to "2026-10-29","limit" to "50")),requests[1]); assertEquals(8,requests.size)
        } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun staleDayResponsesAndFreshDetailRelocationCannotLoseSelectedContext()=check { model,source ->
        model.start(); runCurrent(); source.pages[0].complete(edge()); runCurrent(); model.setMode(AgendaMode.CALENDAR)
        model.load(101,"2026-10-30"); runCurrent(); model.load(101,"2026-10-29"); runCurrent()
        source.pages[2].complete(edge()); source.pages[1].complete(edge().copy(date="2026-10-30")); runCurrent(); assertEquals("2026-10-29",model.state.responseDay)
        model.detail(5602); runCurrent(); model.back(); model.detail(5602); runCurrent()
        val original=JsonContracts.detail(fixture("appointment-101-5602")); val moved=original.copy(appointment=original.appointment.copy(title=null,startAt="2026-10-30T08:00:00Z",endAt="2026-10-30T09:00:00Z"))
        source.details[1].complete(moved); source.details[0].complete(original); runCurrent(); model.back()
        assertNull(model.state.items[0].title); assertEquals(AgendaTimeIssue.OTHER_DAY,display(edge().copy(items=model.state.items)).sourceRows[0].issue)
        assertEquals(AgendaMode.CALENDAR,model.state.mode); assertEquals("2026-10-29",model.state.selection!!.day)
    }
    @Test fun wrongDayEmptyCancellationAndErrorStayUnknownUntilMatchingEmptyResponse()=check { model,source ->
        model.start(); runCurrent(); source.pages[0].complete(edge()); runCurrent(); model.setMode(AgendaMode.CALENDAR)
        model.load(101,"2026-10-29"); runCurrent(); source.pages[1].complete(edge().copy(date="2026-10-28",items=emptyList(),total=0)); runCurrent()
        assertFalse(model.state.showsEmptyResult); assertEquals("2026-10-28",model.state.responseDay)
        model.load(101,"2026-10-29"); runCurrent(); source.pages[2].completeExceptionally(CancellationException()); runCurrent(); assertFalse(model.state.loading); assertFalse(model.state.showsEmptyResult)
        model.load(101,"2026-10-29"); runCurrent(); source.pages[3].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent(); assertEquals(ReadProblem.DENIED,model.state.problem); assertFalse(model.state.showsEmptyResult)
        model.load(101,"2026-10-29"); runCurrent(); source.pages[4].complete(edge().copy(items=emptyList(),total=0)); runCurrent()
        assertTrue(model.state.showsEmptyResult); assertEquals(AgendaMode.CALENDAR,model.state.mode)
    }
    @Test fun businessSwitchAndCancelledDetailInvalidateOldSuccessAndRetainRetryPath()=check { model,source ->
        model.start(); runCurrent(); source.pages[0].complete(edge()); runCurrent(); model.setMode(AgendaMode.CALENDAR); model.detail(5601); runCurrent()
        model.load(202,"2026-10-29"); runCurrent(); source.pages[1].complete(edge().copy(business=202,items=emptyList(),total=0)); source.details[0].complete(JsonContracts.detail(fixture("appointment-101-5601"))); runCurrent()
        assertNull(model.state.detail); assertEquals(202,model.state.selection!!.business.id); assertEquals(AgendaMode.CALENDAR,model.state.mode)
        model.load(101,"2026-10-29"); runCurrent(); source.pages[2].complete(edge()); runCurrent(); model.detail(5601); runCurrent(); source.details[1].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(model.state.detailLoading); assertEquals(ReadProblem.UNAVAILABLE,model.state.detailProblem); assertNull(model.state.detail)
    }
}
