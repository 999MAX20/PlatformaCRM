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
class AppointmentRelationsTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun parent(id: Int=501)=JsonContracts.detail(fixture("appointment-101-$id"))
    private fun profile(b: Int=101)=JsonContracts.clientProfile(fixture(if(b==101) "client-101-7001" else "client-202-7003"))
    private fun task(id: Int=1301)=JsonContracts.taskDetails(fixture("task-101-$id"))
    private inner class Controlled : AgendaRepository,AppointmentRelatedRepository {
        val profiles=mutableListOf<CompletableDeferred<ClientProfile>>(); val tasks=mutableListOf<CompletableDeferred<TaskDetails>>()
        val clientRequests=mutableListOf<Pair<Int,Int>>(); val taskRequests=mutableListOf<Pair<Int,Int>>()
        override suspend fun bootstrap()=JsonContracts.bootstrap(fixture("bootstrap"))
        override suspend fun appointments(business: Int,day: String)=JsonContracts.appointments(fixture("appointments-$business"))
        override suspend fun appointment(business: Int,id: Int)=JsonContracts.detail(fixture("appointment-$business-$id"))
        override suspend fun clientProfile(business: Int,id: Int): ClientProfile { clientRequests+=business to id; return CompletableDeferred<ClientProfile>().also { profiles+=it }.await() }
        override suspend fun taskDetails(business: Int,id: Int): TaskDetails { taskRequests+=business to id; return CompletableDeferred<TaskDetails>().also { tasks+=it }.await() }
    }
    private fun check(block: suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val links=AppointmentRelationsViewModel(source);val model=AgendaViewModel(source,initialDay={"2026-10-28"},relations=links)
        try { model.start();runCurrent();model.detail(501);runCurrent();block(model,links,source) }
        finally { model.viewModelScope.cancel();links.clear();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();Dispatchers.resetMain() }
    }
    @Test fun explicitClientPairAndProvidedTaskWindowAreRequired() {
        val p=parent();assertEquals(7001,p.appointment.clientID);assertEquals(7001,p.clientRefID);assertEquals(7001,p.linkedClientID)
        assertEquals((1301..1305).toList(),p.providedTasks!!.map { it.id });assertTrue(p.relatedTaskWindowCapped)
        assertNull(p.copy(clientRefID=7002).linkedClientID);assertTrue(p.copy(clientRefID=7002).clientLinkAmbiguous)
        assertNull(p.copy(appointment=p.appointment.copy(clientID=null)).linkedClientID)
        assertNull(p.copy(clientRefID=null).linkedClientID);assertNull(p.copy(clientRefID=0).linkedClientID)
        assertNull(p.copy(relatedTasks=null).providedTasks);assertNull(p.copy(maxRelated=null).providedTasks)
        assertNull(p.copy(maxRelated=0).providedTasks);assertNull(p.copy(maxRelated=4).providedTasks)
        assertNull(p.copy(relatedTasks=listOf(p.relatedTasks!![0],p.relatedTasks[0])).providedTasks)
        assertTrue(parent(502).providedTasks!!.isEmpty());assertFalse(parent(502).relatedTaskWindowCapped)
    }
    @Test fun absentNullConflictAndLeadFieldsNeverGuessAClientOrTaskRelation() {
        val j=JSONObject(fixture("appointment-101-501"));j.getJSONObject("appointment").put("client_id",JSONObject.NULL).put("lead_id",7001)
        j.getJSONObject("details").put("client",JSONObject.NULL);j.remove("related");j.remove("payload_budget")
        val p=JsonContracts.detail(j.toString());assertNull(p.linkedClientID);assertNull(p.providedTasks)
        val t=JSONObject(fixture("task-101-1301"));t.getJSONObject("details").put("appointment_id",JSONObject.NULL)
        assertNull(JsonContracts.taskDetails(t.toString()).appointmentID)
        t.getJSONObject("details").put("appointment_id","501")
        try { JsonContracts.taskDetails(t.toString());fail() } catch(e: ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
    }
    @Test fun actualAppointmentClientTaskAndLayeredBackPreserveUnrelatedSearchContexts()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport { r -> requests+=r;val b=r.query["business"];val id=r.path.trimEnd('/').substringAfterLast('/');val file=when {
            r.path.endsWith("/bootstrap/")->"bootstrap";r.path.endsWith("/appointments/")->"appointments-$b";r.path.endsWith("/clients/")->"clients-$b";r.path.endsWith("/tasks/")->"tasks-$b"
            r.path.contains("/appointments/")->"appointment-$b-$id";r.path.contains("/clients/")->"client-$b-$id";else->"task-$b-$id" };ReadResponse(200,fixture(file)) })
        val links=AppointmentRelationsViewModel(repo);val a=AgendaViewModel(repo,initialDay={"2026-10-28"},relations=links);val directory=ClientDirectoryViewModel(repo);val tasks=TaskListViewModel(repo)
        try {
            directory.load(101);tasks.load(101);runCurrent();directory.search("Alpha");tasks.search("Alpha");tasks.filter("open")
            a.start();runCurrent();a.setMode(AgendaMode.CALENDAR);a.detail(501);runCurrent();val notes=a.state.detail!!.notes
            links.openClient();runCurrent();assertEquals(7001,links.profile.state.detail!!.client.id);assertEquals("appointment-7001@example.invalid",links.profile.state.detail!!.client.email)
            links.back();assertEquals(501,a.state.detailID);assertEquals(notes,a.state.detail!!.notes)
            links.openTask(1301);runCurrent();assertEquals(501,links.state.task!!.appointmentID);links.back();assertNull(links.profile.state.detail)
            a.back();assertNull(links.state.request);assertNull(links.state.selected);assertEquals(AgendaMode.CALENDAR,a.state.mode);assertEquals("2026-10-28",a.state.selection!!.day)
            assertEquals("Alpha",directory.state.query);assertEquals("Alpha",tasks.state.query);assertEquals("open",tasks.state.status)
            assertTrue(requests.any { it.path=="/api/mobile/v1/clients/7001/" });assertTrue(requests.any { it.path=="/api/mobile/v1/tasks/1301/" })
        } finally { listOf(a,links,links.profile,directory,tasks).forEach { it.viewModelScope.cancel() };Dispatchers.resetMain() }
    }
    @Test fun childClientDenialWrongIdAndBusinessNeverFallbackToParentOrDirectory()=check { _,links,s ->
        links.openClient();runCurrent();assertNull(links.profile.state.detail);s.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent()
        assertEquals(ReadProblem.DENIED,links.profile.state.problem);assertNull(links.profile.state.detail)
        links.openClient();runCurrent();s.profiles[1].complete(profile().copy(client=profile().client.copy(id=701)));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,links.profile.state.problem)
        links.openClient();runCurrent();s.profiles[2].complete(profile(202));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,links.profile.state.problem)
        links.openClient();runCurrent();s.profiles[3].complete(profile());runCurrent();assertEquals(7001,links.profile.state.detail!!.client.id)
    }
    @Test fun providedTaskStillNeedsIndependentIdentityBusinessAndBacklink()=check { _,links,s ->
        links.openTask(1101);runCurrent();assertTrue(s.taskRequests.isEmpty())
        val invalid=listOf(task().copy(appointmentID=null),task().copy(appointmentID=502),task().copy(business=202),task().copy(task=task().task.copy(id=1302)))
        invalid.forEachIndexed { index,d -> links.openTask(1301);runCurrent();s.tasks[index].complete(d);runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,links.state.problem);assertNull(links.state.task) }
        links.openTask(1301);runCurrent();s.tasks[4].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,links.state.problem)
        links.openTask(1301);runCurrent();s.tasks[5].complete(task());runCurrent();assertNotNull(links.state.task)
    }
    @Test fun parentRetryAndOldUiTokenCannotRepopulateOrStartOldClientRead()=check { a,links,s ->
        val old=links.state.request!!;links.openClient(old);runCurrent();a.detail(501);runCurrent();val fresh=links.state.request!!;assertNotEquals(old,fresh)
        s.profiles[0].complete(profile());runCurrent();assertNull(links.profile.state.detail);assertNull(links.state.selected)
        links.openClient(old);runCurrent();assertEquals(1,s.clientRequests.size)
        links.openClient(fresh);runCurrent();s.profiles[1].complete(profile().copy(client=profile().client.copy(phone=null,email=null)));runCurrent();assertNull(links.profile.state.detail!!.client.phone)
    }
    @Test fun repeatedTaskBackReopenAndLateSuccessCannotRestoreRedactedData()=check { _,links,s ->
        links.openTask(1301);runCurrent();links.openTask(1301);runCurrent()
        s.tasks[1].complete(task().copy(task=task().task.copy(title=null)));s.tasks[0].complete(task());runCurrent();assertNull(links.state.task!!.task.title);assertNull(links.state.tasks!![0].title)
        links.openTask(1301);runCurrent();links.back();links.openTask(1301);runCurrent();s.tasks[3].complete(task());s.tasks[2].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));runCurrent();assertNull(links.state.problem)
        links.openTask(1301);runCurrent();links.back();s.tasks[4].complete(task());runCurrent();assertNull(links.state.task);assertNull(links.state.selected)
    }
    @Test fun businessSwitchParentBackAndDifferentParentClearAllDependentState()=check { a,links,s ->
        links.openClient();runCurrent();a.load(202,"2026-10-28");runCurrent();s.profiles[0].complete(profile());runCurrent();assertNull(links.profile.state.detail);assertNull(links.state.request)
        a.detail(601);runCurrent();links.openClient();runCurrent();s.profiles[1].complete(profile(202));runCurrent();assertEquals(202,links.profile.state.business)
        a.back();assertNull(links.profile.state.detail);assertNull(links.state.parent)
        a.load(101,"2026-10-28");runCurrent();a.detail(501);runCurrent();links.openTask(1301);runCurrent();a.detail(502);runCurrent();s.tasks[0].complete(task());runCurrent()
        assertEquals(502,links.state.parent!!.appointment.id);assertNull(links.state.task);assertNull(links.state.selected)
    }
    @Test fun ambiguousOrUnknownWindowBlocksOnlyThatTransition()=check { _,links,s ->
        val request=links.state.request!!;links.bind(parent().copy(clientRefID=7002),request);links.openClient();runCurrent();assertTrue(s.clientRequests.isEmpty())
        links.openTask(1301);runCurrent();s.tasks[0].complete(task());runCurrent();assertNotNull(links.state.task)
        links.bind(parent().copy(relatedTasks=null),request);links.openTask(1301);runCurrent();assertEquals(1,s.taskRequests.size)
        links.openClient();runCurrent();s.profiles[0].complete(profile());runCurrent();assertNotNull(links.profile.state.detail)
    }
    @Test fun cancelledChildrenRecoverAndClosedParentRejectsLateReplies()=check { a,links,s ->
        links.openClient();runCurrent();s.profiles[0].completeExceptionally(CancellationException());runCurrent();assertFalse(links.profile.state.loading);assertNull(links.profile.state.detail)
        links.openTask(1301);runCurrent();s.tasks[0].completeExceptionally(CancellationException());runCurrent();assertNull(links.state.selected);assertEquals(501,a.state.detailID)
        links.openClient();runCurrent();a.back();s.profiles[1].complete(profile());runCurrent();assertNull(links.state.selected);assertNull(links.profile.state.detail);assertNull(links.state.request)
    }
}
