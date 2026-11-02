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

@OptIn(ExperimentalCoroutinesApi::class)
class HomeTodayTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun home(b: Int = 101) = JsonContracts.home(fixture("home-$b"))
    private fun today(b: Int = 101) = JsonContracts.today(fixture("today-$b"))
    private class Controlled : HomeTodayRepository {
        val homes = mutableListOf<CompletableDeferred<HomeSummary>>()
        val days = mutableListOf<CompletableDeferred<TodaySummary>>()
        override suspend fun home(business: Int) = CompletableDeferred<HomeSummary>().also { homes += it }.await()
        override suspend fun today(business: Int, day: String) = CompletableDeferred<TodaySummary>().also { days += it }.await()
    }
    private fun check(block: suspend TestScope.(HomeTodayViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val source = Controlled(); val model = HomeTodayViewModel(source)
        try { block(model, source) } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun consumedNavigationDoesNotReplayWhenACompositionAttachesAgain() = check { model,s ->
        model.start(101,"2026-10-28"); runCurrent(); s.homes[0].complete(home()); s.days[0].complete(today()); runCurrent()
        model.open(HomeDestination.INBOX)
        assertTrue(model.state.navigationPending); assertEquals(HomeDestination.INBOX,model.takeNavigation())
        assertFalse(model.state.navigationPending); assertEquals(HomeDestination.INBOX,model.state.destination)
        // A second consumer represents a reattached composition on the same retained model.
        assertNull(model.takeNavigation()); assertEquals(HomeDestination.INBOX,model.state.destination)
        assertNotNull(model.state.home); assertNotNull(model.state.today)
    }
    @Test fun anExplicitRepeatedDestinationProducesANewSingleNavigation() = check { model,_ ->
        model.start(101,"2026-10-28"); runCurrent()
        model.open(HomeDestination.CLIENTS); assertEquals(HomeDestination.CLIENTS,model.takeNavigation()); assertNull(model.takeNavigation())
        model.open(HomeDestination.CLIENTS); assertEquals(HomeDestination.CLIENTS,model.takeNavigation()); assertNull(model.takeNavigation())
        model.open(HomeDestination.TASKS); assertEquals(HomeDestination.TASKS,model.takeNavigation()); assertNull(model.takeNavigation())
    }
    @Test fun backAndBusinessResetRevokePendingHomeNavigation() = check { model,_ ->
        model.start(101,"2026-10-28"); runCurrent(); model.open(HomeDestination.INBOX); model.back()
        assertNull(model.takeNavigation()); assertNull(model.state.destination); assertFalse(model.state.navigationPending)
        model.open(HomeDestination.CLIENTS); model.start(202,"2026-10-28"); runCurrent()
        assertNull(model.takeNavigation()); assertNull(model.state.destination)
        model.open(HomeDestination.TASKS); model.clear(); assertNull(model.takeNavigation()); assertFalse(model.state.navigationPending)
    }
    @Test fun unattachedOrNewModelsDoNotRecreateAnOldHomeNavigation() = check { model,_ ->
        model.open(HomeDestination.INBOX); assertNull(model.takeNavigation()); assertNull(model.state.destination)
        model.start(101,"2026-10-28"); runCurrent(); model.open(HomeDestination.INBOX); assertEquals(HomeDestination.INBOX,model.takeNavigation())
        val fresh = HomeTodayViewModel(Controlled())
        try { assertNull(fresh.takeNavigation()); assertNull(fresh.state.destination); assertFalse(fresh.state.navigationPending) }
        finally { fresh.viewModelScope.cancel() }
    }
    @Test fun exactSourceRoutesAndInvalidContextMakesNoRequest() = runTest {
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { requests += it; ReadResponse(200, fixture(if (it.path.endsWith("/home/")) "home-101" else "today-101")) })
        assertTrue(repo.home(101).validFor(101)); assertTrue(repo.today(101, "2026-10-28").validFor(101, "2026-10-28"))
        assertEquals(listOf(ReadRequest("/api/mobile/v1/home/", mapOf("business" to "101", "limit" to "5")), ReadRequest("/api/mobile/v1/today/", mapOf("business" to "101", "date" to "2026-10-28", "limit" to "20"))), requests)
        try { repo.today(101, "2026-02-30"); fail() } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, e.problem) }
        assertEquals(2, requests.size)
    }
    @Test fun summariesAreSourceCountsMissingIsUnavailableAndWrongTypesFail() {
        val j = JSONObject(fixture("home-101")); j.getJSONObject("sections").getJSONObject("tasks").put("open", 73)
        assertEquals(73, JsonContracts.home(j.toString()).tasks!!.open)
        j.put("sections", JSONObject()); val hidden = JsonContracts.home(j.toString())
        assertTrue(hidden.validFor(101)); assertNull(hidden.tasks); assertNull(hidden.conversations); assertNull(hidden.appointments)
        assertFalse(home().copy(business = 202).validFor(101)); assertFalse(home().copy(tasks = HomeTasks(-1)).validFor(101))
        assertFalse(home().copy(conversations = HomeConversations(0,1)).validFor(101))
        j.put("sections", JSONObject().put("tasks", JSONObject().put("open", "2")))
        try { JsonContracts.home(j.toString()); fail() } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, e.problem) }
    }
    @Test fun todayRejectsWrongScopeDayDuplicatesTimesAndWindow() {
        val t = today(); val a = t.appointments!!
        assertFalse(t.copy(business = 202).validFor(101, t.date)); assertFalse(t.validFor(101, "2026-10-29"))
        assertFalse(t.copy(appointments = a.copy(date = "2026-10-27")).validFor(101,t.date))
        assertFalse(t.copy(appointments = a.copy(items = listOf(a.items[0],a.items[0]))).validFor(101,t.date))
        assertFalse(t.copy(appointments = a.copy(items = listOf(a.items[0].copy(endAt = a.items[0].startAt)))).validFor(101,t.date))
        assertFalse(t.copy(limit = 1, maxItems = 1).validFor(101,t.date)); assertFalse(t.copy(maxItems = 0).validFor(101,t.date))
        assertTrue(t.copy(appointments = a.copy(total = 99)).appointments!!.partial)
        assertFalse(t.copy(tasks = t.tasks!!.copy(overdue = -1)).validFor(101,t.date))
    }
    @Test fun validEmptyAndWithheldSectionsDifferFromPartial() {
        val t = today(); val empty = t.copy(appointments = t.appointments!!.copy(total = 0, items = emptyList()), tasks = null)
        assertTrue(empty.validFor(101,t.date)); assertFalse(empty.appointments!!.partial); assertNull(empty.tasks)
        assertTrue(empty.copy(appointments = empty.appointments.copy(total = 1)).appointments!!.partial)
    }
    @Test fun independentFailureAndRetryKeepsOtherProjectionAndNavigationContext() = check { model, source ->
        model.start(101,"2026-10-28"); runCurrent(); source.homes[0].complete(home()); source.days[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertNotNull(model.state.home); assertEquals(ReadProblem.DENIED, model.state.todayProblem); assertNull(model.state.today)
        model.open(HomeDestination.CLIENTS); model.back(); assertNotNull(model.state.home); assertEquals("2026-10-28",model.state.day)
        model.start(101,"2026-10-28"); runCurrent(); assertEquals(1,source.homes.size)
        model.reloadToday(); runCurrent(); source.days[1].complete(today()); runCurrent()
        assertNull(model.state.todayProblem); assertNotNull(model.state.home); assertNotNull(model.state.today)
    }
    @Test fun retriesCannotRestoreOldCountsAndBusinessSwitchInvalidatesBoth() = check { model, source ->
        model.start(101,"2026-10-28"); runCurrent(); model.reloadHome(); runCurrent()
        source.homes[1].complete(home().copy(tasks = null)); source.homes[0].complete(home()); runCurrent(); assertNull(model.state.home!!.tasks)
        model.open(HomeDestination.TASKS); model.start(202,"2026-10-28"); runCurrent(); assertNull(model.state.destination); assertNull(model.state.home)
        source.days[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); source.homes[2].complete(home(202)); source.days[1].complete(today(202)); runCurrent()
        assertEquals(202,model.state.today!!.business); assertNull(model.state.todayProblem)
    }
    @Test fun clearDayChangeCancellationAndWrongPayloadStayRecoverable() = check { model, source ->
        model.start(101,"2026-10-28"); runCurrent(); model.clear(); source.homes[0].complete(home()); source.days[0].complete(today()); runCurrent(); assertNull(model.state.home)
        model.start(101,"2026-10-29"); runCurrent(); source.homes[1].completeExceptionally(CancellationException()); source.days[1].complete(today()); runCurrent()
        assertFalse(model.state.homeLoading); assertNull(model.state.homeProblem); assertNull(model.state.home); assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.todayProblem)
        model.reloadHome(); runCurrent(); source.homes[2].complete(home()); runCurrent(); assertNotNull(model.state.home)
    }
    @Test fun sectionThenIndependentTaskDetailAndBackRetainsBothContexts() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val repo = APIReadRepository(ReadTransport { request -> ReadResponse(200, fixture(when {
            request.path.endsWith("/home/") -> "home-101"
            request.path.endsWith("/today/") -> "today-101"
            request.path.endsWith("/tasks/") -> "tasks-101"
            else -> "task-101-1101"
        })) })
        val h = HomeTodayViewModel(repo); val tasks = TaskListViewModel(repo)
        try {
            h.start(101,"2026-10-28"); runCurrent()
            HomeDestination.entries.forEach { h.open(it); assertEquals(it,h.state.destination); assertTrue(it.tabIndex in 1..4); h.back() }
            h.open(HomeDestination.TASKS); tasks.load(101); runCurrent(); tasks.search("Alpha"); tasks.filter("open"); tasks.open(1101); runCurrent()
            assertEquals(1101,tasks.state.detail!!.task.id); tasks.back(); h.back()
            assertEquals("Alpha",tasks.state.query); assertEquals("open",tasks.state.status); assertNotNull(h.state.today); assertNull(h.state.destination)
        } finally { h.viewModelScope.cancel(); tasks.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun remainingSectionRoutesReadTheirOwnDetailsAndRetainContext() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val files = mapOf("bootstrap/" to "bootstrap", "home/" to "home-101", "today/" to "today-101", "appointments/" to "appointments-101", "appointments/501/" to "appointment-101-501", "clients/" to "clients-101", "clients/701/" to "client-101-701", "inbox/" to "inbox-101", "inbox/901/" to "inbox-101-901")
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { request -> requests += request; files[request.path.removePrefix("/api/mobile/v1/")]?.let { ReadResponse(200,fixture(it)) } ?: ReadResponse(404,"") })
        val home = HomeTodayViewModel(repo); val agenda = AgendaViewModel(repo, initialDay = { "2026-10-28" })
        val clients = ClientDirectoryViewModel(repo); val profile = ClientProfileViewModel(repo); val inbox = InboxViewModel(repo)
        try {
            home.start(101,"2026-10-28"); runCurrent(); home.open(HomeDestination.APPOINTMENTS); agenda.start(); runCurrent(); agenda.detail(501); runCurrent()
            assertEquals(501,agenda.state.detail!!.appointment.id); agenda.back(); home.back()
            assertEquals("2026-10-28",agenda.state.selection!!.day); assertEquals(2,agenda.state.items.size)
            home.open(HomeDestination.CLIENTS); clients.load(101); runCurrent(); clients.search("Alpha"); clients.open(701)
            profile.load(101,701,clients::refreshContact); runCurrent(); assertEquals(701,profile.state.detail!!.client.id)
            profile.clear(); clients.back(); home.back(); assertEquals("Alpha",clients.state.query); assertEquals(1,clients.state.visible.size)
            home.open(HomeDestination.INBOX); inbox.load(101); runCurrent(); inbox.search("Alpha"); inbox.unreadOnly(true); inbox.open(901); runCurrent()
            assertEquals(901,inbox.state.thread!!.conversation.id); inbox.back(); home.back()
            assertEquals("Alpha",inbox.state.query); assertTrue(inbox.state.unreadOnly); assertEquals(1,inbox.state.visible.size)
            assertNotNull(home.state.today); assertNull(home.state.destination)
            assertEquals(1,requests.count { it.path.endsWith("/home/") }); assertEquals(1,requests.count { it.path.endsWith("/today/") })
        } finally { listOf(home,agenda,clients,profile,inbox).forEach { it.viewModelScope.cancel() }; Dispatchers.resetMain() }
    }
}
