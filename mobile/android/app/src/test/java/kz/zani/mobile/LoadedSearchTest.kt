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
class LoadedSearchTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun source(kind: LoadedSearchKind, rows: List<LoadedSearchRow> = listOf(LoadedSearchRow(9, "Same title")), business: Int = 101, epoch: Int = 1, coverage: LoadedSearchCoverage = LoadedSearchCoverage.LOADED) =
        LoadedSearchSource(kind, LoadedSearchToken(kind, business, epoch, 1), coverage, rows)
    private fun feed(sources: List<LoadedSearchSource>, business: Int = 101, epoch: Int = 1) = LoadedSearchFeed.create(business, epoch, sources)
    private inner class Transport : ReadTransport {
        val requests = mutableListOf<ReadRequest>(); val pending = mutableListOf<CompletableDeferred<ReadResponse>>()
        val overrides = mutableMapOf<String, ReadResponse>(); var holdDetails = false
        override suspend fun get(request: ReadRequest): ReadResponse {
            requests += request
            overrides.remove(request.path)?.let { return it }
            val tail = request.path.trimEnd('/').substringAfterLast('/')
            if (holdDetails && tail.toIntOrNull() != null) return CompletableDeferred<ReadResponse>().also { pending += it }.await()
            val b = request.query["business"]
            val name = if (tail.toIntOrNull() == null) when (tail) {
                "bootstrap" -> "bootstrap"; "appointments" -> "appointments-$b"; "clients" -> "clients-$b"; "inbox" -> "inbox-$b"; else -> "tasks-$b"
            } else when {
                request.path.contains("/appointments/") -> "appointment-$b-$tail"; request.path.contains("/clients/") -> "client-$b-$tail"
                request.path.contains("/inbox/") -> "inbox-$b-$tail"; else -> "task-$b-$tail"
            }
            return ReadResponse(200, fixture(name))
        }
    }
    private inner class Harness {
        val transport = Transport(); val repo = APIReadRepository(transport)
        val agenda = AgendaViewModel(repo, initialDay = { "2026-10-28" })
        val clients = ClientDirectoryViewModel(repo); val inbox = InboxViewModel(repo); val tasks = TaskListViewModel(repo)
        val search = LoadedSearchViewModel(repo)
        fun reconcile() = search.reconcile(LoadedSearchSources.feed(agenda.state, clients.state, inbox.state, tasks.state))
        fun loadSources() { val epoch = agenda.state.businessEpoch; clients.load(101, epoch); inbox.load(101, epoch); tasks.load(101, epoch) }
        fun all() = listOf(agenda, clients, inbox, tasks, search, search.profile)
    }
    private fun check(block: suspend TestScope.(Harness) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val h = Harness()
        try { h.agenda.start(); runCurrent(); h.reconcile(); block(h) }
        finally { h.all().forEach { it.viewModelScope.cancel() }; Dispatchers.resetMain() }
    }
    @Test fun typedIdentitiesAndLoadedOrderNeverJoinSameTitlesOrNumericIDs() {
        val rows = listOf(LoadedSearchRow(12,"same title"), LoadedSearchRow(9,"Same title"))
        val f = feed(listOf(source(LoadedSearchKind.TASKS), source(LoadedSearchKind.INBOX), source(LoadedSearchKind.CLIENTS), source(LoadedSearchKind.APPOINTMENTS, rows)))
        val hits = f.matches(" SAME ")
        assertEquals(listOf(12,9,9,9,9),hits.map { it.identity.id }); assertEquals(5,hits.map { it.identity }.distinct().size)
        assertEquals(listOf(LoadedSearchKind.APPOINTMENTS,LoadedSearchKind.APPOINTMENTS,LoadedSearchKind.CLIENTS,LoadedSearchKind.INBOX,LoadedSearchKind.TASKS),hits.map { it.identity.kind })
        assertEquals(4,f.matches("same",setOf(hits.last().identity)).size); assertTrue(f.matches("  ").isEmpty()); assertTrue(f.matches("absent").isEmpty())
    }
    @Test fun foreignEpochUntaggedInvalidDuplicateAndUnavailableSourcesAreParked() {
        val s = source(LoadedSearchKind.TASKS)
        assertFalse(feed(listOf(s),business=202).hasLoadedSource); assertFalse(feed(listOf(s),epoch=2).hasLoadedSource)
        assertFalse(feed(listOf(s.copy(token=null))).hasLoadedSource)
        assertEquals(LoadedSearchCoverage.UNAVAILABLE,feed(listOf(s,s)).source(s.kind)!!.coverage)
        assertFalse(feed(listOf(s.copy(rows=s.rows+s.rows))).hasLoadedSource)
        assertFalse(feed(listOf(s.copy(rows=listOf(LoadedSearchRow(0,"Same title"))))).hasLoadedSource)
        listOf(LoadedSearchCoverage.NOT_LOADED,LoadedSearchCoverage.LOADING,LoadedSearchCoverage.DENIED,LoadedSearchCoverage.UNAVAILABLE).forEach { status ->
            val f=feed(listOf(s.copy(coverage=status))); assertFalse(f.hasLoadedSource);assertTrue(f.matches("same").isEmpty());assertTrue(f.source(s.kind)!!.rows.isEmpty())
        }
        val partial=feed(listOf(s.copy(coverage=LoadedSearchCoverage.PARTIAL)));assertEquals(1,partial.matches("same").size)
        assertTrue(feed(listOf(s.copy(rows=listOf(LoadedSearchRow(1,null),LoadedSearchRow(2," "))))).matches("unavailable").isEmpty())
        assertEquals(4,feed(emptyList()).sources.size); assertFalse(feed(emptyList()).hasLoadedSource)
    }
    @Test fun searchDoesNotLoadSectionsOrFetchOnQueryAndDoesNotAssertUnknownEmpty()=check { h ->
        h.search.search("synthetic");assertEquals(2,h.search.state.matches.size);assertEquals(2,h.transport.requests.size)
        assertEquals(LoadedSearchCoverage.NOT_LOADED,h.search.state.feed.source(LoadedSearchKind.CLIENTS)!!.coverage)
        h.search.search("absent");assertTrue(h.search.state.showsNoMatches);assertEquals(2,h.transport.requests.size)
        h.search.reconcile(LoadedSearchFeed.create(null,0,emptyList()));h.search.search("absent");assertFalse(h.search.state.showsNoMatches)
    }
    @Test fun realAdaptersExposeOnlyLoadedTitlesAndIgnoreSourceFilters()=check { h ->
        h.loadSources();runCurrent();h.clients.search("Beta");h.inbox.search("response");h.inbox.unreadOnly(true);h.tasks.search("review");h.tasks.filter("done");h.reconcile()
        h.search.search("synthetic");assertEquals(9,h.search.state.matches.size)
        listOf("+70000000001","alpha@example.invalid","operator response","profile note","follow-up comment","task context","7001","/app/calendar").forEach { hidden -> h.search.search(hidden);assertTrue(hidden,h.search.state.matches.isEmpty()) }
        h.search.search("beta");assertEquals(listOf(LoadedSearchKind.CLIENTS,LoadedSearchKind.INBOX,LoadedSearchKind.TASKS),h.search.state.matches.map { it.identity.kind })
        assertEquals(5,h.transport.requests.size)
    }
    @Test fun allFourIndependentDetailsAndBackPreserveQueryOrderDayModeAndModuleQueries()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("synthetic");h.agenda.setMode(AgendaMode.CALENDAR)
        h.clients.search("Beta");h.inbox.search("response");h.inbox.unreadOnly(true);h.tasks.search("review");h.tasks.filter("done")
        val hits=h.search.state.matches;val before=h.transport.requests.size
        LoadedSearchKind.entries.forEach { kind ->
            val hit=hits.first { it.identity.kind==kind };h.search.open(hit);runCurrent()
            assertNull(h.search.state.problem);assertFalse(h.search.state.loading);assertTrue(h.search.state.detail!=null || h.search.profile.state.detail!=null)
            h.search.back();assertEquals("synthetic",h.search.state.query);assertEquals(hits,h.search.state.matches);assertNull(h.search.profile.state.detail)
        }
        assertEquals(before+4,h.transport.requests.size)
        assertEquals(listOf("/api/mobile/v1/appointments/501/","/api/mobile/v1/clients/701/","/api/mobile/v1/inbox/901/","/api/mobile/v1/tasks/1101/"),h.transport.requests.takeLast(4).map { it.path })
        assertEquals("Beta",h.clients.state.query);assertEquals("response",h.inbox.state.query);assertTrue(h.inbox.state.unreadOnly);assertEquals("review",h.tasks.state.query);assertEquals("done",h.tasks.state.status)
        assertEquals(AgendaMode.CALENDAR,h.agenda.state.mode);assertEquals("2026-10-28",h.agenda.state.selection!!.day)
        assertNull(h.agenda.state.detailID);assertNull(h.clients.state.selectedID);assertNull(h.inbox.state.selectedID);assertNull(h.tasks.state.selectedID)
    }
    @Test fun deniedResultAndSuccessfulRetryDoNotRestoreOldCandidateUntilSourceRefresh()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("Alpha");val hit=h.search.state.matches.first { it.identity.kind==LoadedSearchKind.TASKS }
        h.transport.holdDetails=true;h.search.open(hit);runCurrent();h.transport.pending[0].complete(ReadResponse(403,""));runCurrent()
        assertEquals(ReadProblem.DENIED,h.search.state.problem);assertNull(h.search.state.detail);assertFalse(h.search.state.matches.contains(hit))
        h.search.open(hit,retry=true);runCurrent();h.transport.pending[1].complete(ReadResponse(200,fixture("task-101-1101")));runCurrent()
        assertNotNull(h.search.state.detail);assertFalse(h.search.state.matches.contains(hit));h.search.back()
        val before=h.transport.requests.size;h.search.open(hit);runCurrent();assertEquals(before,h.transport.requests.size)
        h.tasks.load(101,h.agenda.state.businessEpoch);runCurrent();h.reconcile();assertTrue(h.search.state.matches.any { it.identity==hit.identity });assertEquals("Alpha",h.search.state.query)
    }
    @Test fun freshWithheldTitleAndBackReopenIgnoreLateError()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("Alpha");val hit=h.search.state.matches.first { it.identity.kind==LoadedSearchKind.INBOX }
        h.transport.holdDetails=true;h.search.open(hit);runCurrent();h.search.back();h.search.open(hit);runCurrent()
        val redacted=JSONObject(fixture("inbox-101-901"));redacted.getJSONObject("conversation").put("title",JSONObject.NULL)
        h.transport.pending[1].complete(ReadResponse(200,redacted.toString()));runCurrent();h.transport.pending[0].complete(ReadResponse(403,""));runCurrent()
        assertNull(h.search.state.detail!!.title);assertNull(h.search.state.problem);assertFalse(h.search.state.matches.contains(hit));h.search.back();assertFalse(h.search.state.matches.contains(hit))
    }
    @Test fun refreshDeniedSourceClearsPendingSelectionAndNeverFallsBack()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("Alpha");val hit=h.search.state.matches.first { it.identity.kind==LoadedSearchKind.TASKS }
        h.transport.holdDetails=true;h.search.open(hit);runCurrent()
        h.transport.overrides["/api/mobile/v1/tasks/"]=ReadResponse(403,"");h.tasks.load(101,h.agenda.state.businessEpoch);h.reconcile()
        assertNull(h.search.state.selected);assertEquals(LoadedSearchCoverage.LOADING,h.search.state.feed.source(LoadedSearchKind.TASKS)!!.coverage)
        runCurrent();h.reconcile();h.transport.pending[0].complete(ReadResponse(200,fixture("task-101-1101")));runCurrent()
        assertEquals(LoadedSearchCoverage.DENIED,h.search.state.feed.source(LoadedSearchKind.TASKS)!!.coverage);assertNull(h.search.state.detail);assertTrue(h.search.state.matches.none { it.identity.kind==LoadedSearchKind.TASKS })
    }
    @Test fun businessRoundTripNeverReindexesOldSnapshotsAndRejectsLateClient()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("Alpha");val epoch=h.agenda.state.businessEpoch;val hit=h.search.state.matches.first { it.identity.kind==LoadedSearchKind.CLIENTS }
        h.transport.holdDetails=true;h.search.open(hit);runCurrent();h.agenda.load(202,"2026-10-28");h.reconcile();runCurrent();h.reconcile()
        h.transport.pending[0].complete(ReadResponse(200,fixture("client-101-701")));runCurrent()
        assertNull(h.search.profile.state.detail);assertNull(h.search.state.selected);assertEquals("",h.search.state.query)
        h.agenda.load(101,"2026-10-28");runCurrent();h.reconcile();h.search.search("synthetic")
        assertTrue(h.agenda.state.businessEpoch>epoch);assertEquals(2,h.search.state.matches.size)
        assertEquals(LoadedSearchCoverage.NOT_LOADED,h.search.state.feed.source(LoadedSearchKind.CLIENTS)!!.coverage)
        h.clients.load(101);runCurrent();h.reconcile();assertEquals(2,h.search.state.matches.size)
        h.clients.load(101,h.agenda.state.businessEpoch);runCurrent();h.reconcile();assertEquals(4,h.search.state.matches.size)
    }
    @Test fun independentReadsValidateBusinessAndIDForEveryKind()=check { h ->
        h.loadSources();runCurrent();h.reconcile();h.search.search("synthetic");val hits=h.search.state.matches;h.transport.holdDetails=true
        LoadedSearchKind.entries.forEach { kind ->
            val hit=hits.first { it.identity.kind==kind };val file=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment-101-501";LoadedSearchKind.CLIENTS->"client-101-701";LoadedSearchKind.INBOX->"inbox-101-901";LoadedSearchKind.TASKS->"task-101-1101"}
            val field=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment";LoadedSearchKind.CLIENTS->"client";LoadedSearchKind.INBOX->"conversation";LoadedSearchKind.TASKS->"task"}
            val wrongBusiness=JSONObject(fixture(file)).put("business",202)
            h.search.open(hit);runCurrent();h.transport.pending.last().complete(ReadResponse(200,wrongBusiness.toString()));runCurrent()
            assertEquals(ReadProblem.INVALID_PAYLOAD,h.search.state.problem);assertNull(h.search.state.detail);assertNull(h.search.profile.state.detail)
            val wrongID=JSONObject(fixture(file));wrongID.getJSONObject(field).put("id",99999)
            h.search.open(hit,retry=true);runCurrent();h.transport.pending.last().complete(ReadResponse(200,wrongID.toString()));runCurrent()
            assertEquals(ReadProblem.INVALID_PAYLOAD,h.search.state.problem);assertFalse(h.search.state.matches.contains(hit));h.search.back()
        }
    }
    @Test fun cancellationBackAndOldUiTokensCannotStrandOrRefetchAResult()=check { h ->
        h.search.search("synthetic");val hit=h.search.state.matches.first();h.transport.holdDetails=true
        h.search.open(hit);runCurrent();h.transport.pending[0].completeExceptionally(CancellationException());runCurrent()
        assertNull(h.search.state.selected);assertFalse(h.search.state.loading);assertTrue(h.search.state.matches.contains(hit))
        h.search.open(hit);runCurrent();h.search.back();h.transport.pending[1].complete(ReadResponse(200,fixture("appointment-101-501")));runCurrent();assertNull(h.search.state.detail)
        h.agenda.load(101,"2026-10-29");runCurrent();h.reconcile();val before=h.transport.requests.size;h.search.open(hit);runCurrent();assertEquals(before,h.transport.requests.size)
    }
    @Test fun unknownAppointmentTimeCanStillOpenByExplicitIdentity()=check { h ->
        h.search.search("synthetic");val hit=h.search.state.matches.first();h.transport.holdDetails=true;h.search.open(hit);runCurrent()
        val j=JSONObject(fixture("appointment-101-501"));j.getJSONObject("appointment").put("start_at",JSONObject.NULL).put("end_at","bad")
        h.transport.pending[0].complete(ReadResponse(200,j.toString()));runCurrent();assertNull(h.search.state.problem);assertNotNull(h.search.state.detail)
    }
    @Test fun sourcePartialAndSourceDayMismatchRemainHonest()=check { h ->
        val j=JSONObject(fixture("tasks-101"));j.getJSONObject("summary").put("total",9);h.transport.overrides["/api/mobile/v1/tasks/"]=ReadResponse(200,j.toString())
        h.tasks.load(101,h.agenda.state.businessEpoch);runCurrent();h.reconcile();h.search.search("synthetic");assertEquals(5,h.search.state.matches.size)
        assertEquals(LoadedSearchCoverage.PARTIAL,h.search.state.feed.source(LoadedSearchKind.TASKS)!!.coverage)
        h.agenda.load(101,"2026-10-29");runCurrent();h.reconcile();assertTrue(h.search.state.matches.none { it.identity.kind==LoadedSearchKind.APPOINTMENTS })
        h.search.search("absent");assertTrue(h.search.state.showsNoMatches)
    }
    @Test fun exactSharedHeaderRowsHitsFeedsKeepRawBytesNilEmptyAndExistingTextMatching() {
        val cases=JSONObject(fixture("loaded-search-exact-header-cases")).getJSONArray("cases")
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val before=row.getString("before_title");val after=if(row.isNull("after_title"))null else row.getString("after_title");val changed=row.getBoolean("changed")
            for(kind in LoadedSearchKind.entries) {val a=LoadedSearchRow(9,before);val b=LoadedSearchRow(9,after);val f=feed(listOf(source(kind,listOf(a))));val g=feed(listOf(source(kind,listOf(b))));val hit=f.matches(" SHARED ").single()
                assertEquals(changed,a!=b);assertEquals(changed,f!=g);assertEquals(!changed,g.contains(hit));assertEquals(before,hit.title);assertEquals(listOf(hit),f.matches(" SHARED "))
                if(after!=null && after.isNotEmpty()){val current=g.matches("shared").single();assertEquals(changed,hit!=current);assertEquals(after,current.title)}else assertTrue(g.matches("shared").isEmpty())
                assertEquals(4,g.sources.size);assertEquals(hit.token,g.source(kind)!!.token);assertEquals(LoadedSearchCoverage.LOADED,g.source(kind)!!.coverage)
            }
        };assertNotEquals(LoadedSearchRow(9,null),LoadedSearchRow(9,""))
    }
}
