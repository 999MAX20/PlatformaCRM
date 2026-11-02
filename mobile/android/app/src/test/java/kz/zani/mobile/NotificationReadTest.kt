package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.NotificationCenterViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class NotificationReadTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun page(business: Int = 101) = JsonContracts.notifications(fixture("notifications-$business"))
    private fun target() = JsonContracts.detail(fixture("appointment-101-501"))
    private class Controlled : NotificationRepository {
        val pages = mutableListOf<CompletableDeferred<NotificationPage>>()
        val targets = mutableListOf<CompletableDeferred<AppointmentDetail>>()
        val ids = mutableListOf<Pair<Int,Int>>()
        override suspend fun notifications(business: Int) = CompletableDeferred<NotificationPage>().also { pages += it }.await()
        override suspend fun appointment(business: Int, id: Int): AppointmentDetail {
            ids += business to id
            return CompletableDeferred<AppointmentDetail>().also { targets += it }.await()
        }
    }
    private fun check(block: suspend TestScope.(NotificationCenterViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val source = Controlled(); val model = NotificationCenterViewModel(source)
        try { model.load(101); runCurrent(); source.pages[0].complete(page()); runCurrent(); block(model, source) }
        finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun existingReadRouteAndNoWriteRequest() = runTest {
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { request -> requests += request; ReadResponse(200, fixture("notifications-101")) })
        assertTrue(repo.notifications(101).validFor(101))
        assertEquals(listOf(ReadRequest("/api/mobile/v1/notifications/", mapOf("business" to "101", "limit" to "50"))), requests)
        try { repo.notifications(0); fail("Invalid scope requested") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, e.problem) }
        assertEquals(1, requests.size)
    }
    @Test fun missingReadMarkerIsUnknownNotUnreadAndTypesStayStrict() {
        val json = JSONObject(fixture("notifications-101")); json.getJSONArray("items").getJSONObject(0).remove("read_at")
        val unknown = JsonContracts.notifications(json.toString()).items[0]
        assertFalse(unknown.readMarkerPresent); assertFalse(unknown.unread)
        assertTrue(page().items[0].unread); assertFalse(page().items[2].unread)
        json.getJSONArray("items").getJSONObject(0).put("read_at", false)
        try { JsonContracts.notifications(json.toString()); fail("Boolean read marker coerced") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, e.problem) }
    }
    @Test fun onlyMatchingRelativeCalendarRoutesAreAccepted() {
        val item = page().items[0]
        for (url in listOf("/app/calendar?appointment=501", "/app/calendar/501", "/app/calendar/501/")) assertEquals(501, item.copy(actionURL = url).appointmentTarget)
        for (url in listOf("https://evil.invalid/app/calendar/501", "//evil.invalid/app/calendar/501", "/app/leads/501", "/app/tasks?task=501", "/app/calendar/999", "/app/calendar?appointment=501&business=202", "/app/calendar?appointment=501&appointment=999", "/app/calendar/501#x", "/app/calendar/%35%30%31", "/x/../app/calendar/501")) assertNull(url, item.copy(actionURL = url).appointmentTarget)
        assertNull(item.copy(appointmentID = null).appointmentTarget); assertNull(item.copy(appointmentID = -1).appointmentTarget)
    }
    @Test fun filtersCardTargetAndTwoBacksPreserveUnreadAndContext() = check { model, source ->
        model.search(" ALPHA "); model.filter("sales"); model.unreadOnly(true)
        assertEquals(listOf(2101), model.state.visible.map { it.id })
        model.open(2101); assertTrue(model.state.selected!!.unread); assertTrue(source.targets.isEmpty())
        model.openTarget(); runCurrent(); assertEquals(listOf(101 to 501), source.ids)
        source.targets[0].complete(target()); runCurrent(); assertEquals(501, model.state.target!!.appointment.id)
        model.back(); assertEquals(2101, model.state.selectedID); assertNull(model.state.target); assertFalse(model.state.targetActive)
        model.back(); assertNull(model.state.selectedID); assertEquals(" ALPHA ", model.state.query); assertTrue(model.state.unreadOnly)
        assertEquals("sales", model.state.category); assertTrue(model.state.items[0].unread); assertEquals(1, source.pages.size)
    }
    @Test fun legacyLinkDoesNotReadOrRedirectAndUnknownIdDoesNotOpen() = check { model, source ->
        model.open(2102); model.openTarget(); runCurrent(); assertTrue(source.targets.isEmpty()); assertFalse(model.state.targetActive)
        model.close(); model.open(999); assertNull(model.state.selectedID)
    }
    @Test fun parentAccessDoesNotGrantTargetAccessAndRetryIsIndependent() = check { model, source ->
        model.open(2101); model.openTarget(); runCurrent(); source.targets[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals(ReadProblem.DENIED, model.state.targetProblem); assertNull(model.state.target); assertTrue(model.state.selected!!.unread)
        model.openTarget(); runCurrent(); source.targets[1].complete(target().copy(business = 202)); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.targetProblem); assertNull(model.state.target)
        model.openTarget(); runCurrent(); source.targets[2].complete(target()); runCurrent(); assertNotNull(model.state.target)
        assertEquals(1, source.pages.size)
    }
    @Test fun targetBackRetryAndBusinessSwitchRejectLateResults() = check { model, source ->
        model.open(2101); model.openTarget(); runCurrent(); model.backTarget(); model.openTarget(); runCurrent()
        source.targets[0].complete(target()); runCurrent(); assertNull(model.state.target); assertTrue(model.state.targetLoading)
        source.targets[1].complete(target().copy(appointment = target().appointment.copy(title = null))); runCurrent(); assertNull(model.state.target!!.appointment.title)
        model.openTarget(); runCurrent(); model.load(101); runCurrent(); model.load(202); runCurrent()
        source.pages[2].complete(page(202)); runCurrent(); source.pages[1].complete(page()); source.targets[2].complete(target()); runCurrent()
        assertEquals(listOf(2201), model.state.items.map { it.id }); assertNull(model.state.target); assertNull(model.state.selectedID)
    }
    @Test fun cancelledTargetAndListRemainRecoverable() = check { model, source ->
        model.search("Alpha"); model.filter("sales"); model.open(2101); model.openTarget(); runCurrent()
        source.targets[0].completeExceptionally(CancellationException()); runCurrent()
        assertEquals(2101, model.state.selectedID); assertFalse(model.state.targetActive); assertEquals("Alpha", model.state.query)
        model.load(101); runCurrent(); source.pages[1].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(model.state.loading); assertFalse(model.state.showsEmpty); assertTrue(model.state.categories.contains("sales"))
        model.load(101); runCurrent(); model.load(null); source.pages[2].complete(page()); runCurrent()
        assertNull(model.state.business); assertTrue(model.state.items.isEmpty())
    }
    @Test fun listFailurePartialAndEmptyRetainFilterAndRejectForeignPage() = check { model, source ->
        model.filter("sales"); model.load(101); runCurrent(); source.pages[1].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertFalse(model.state.showsEmpty); assertTrue(model.state.categories.contains("sales"))
        model.load(101); runCurrent(); source.pages[2].complete(NotificationPage(101, emptyList(), 5)); runCurrent()
        assertTrue(model.state.partial); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[3].complete(NotificationPage(101, emptyList(), 0)); runCurrent(); assertTrue(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[4].complete(page(202)); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.problem); assertTrue(model.state.items.isEmpty())
    }
}
