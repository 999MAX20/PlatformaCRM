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
class ClientWorkTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun profile(b: Int = 101, id: Int = 701) = JsonContracts.clientProfile(fixture("client-$b-$id"))
    private fun task() = JsonContracts.taskDetails(fixture("task-101-1401"))
    private fun thread() = JsonContracts.thread(fixture("inbox-101-931"))
    private fun appointment() = JsonContracts.detail(fixture("appointment-101-5101"))
    private class Controlled(val fixture: (String) -> String) : ClientProfileRepository, ClientWorkRepository {
        val tasks = mutableListOf<CompletableDeferred<TaskDetails>>()
        val threads = mutableListOf<CompletableDeferred<InboxThread>>()
        val appointments = mutableListOf<CompletableDeferred<AppointmentDetail>>()
        val requests = mutableListOf<Triple<String,Int,Int>>()
        override suspend fun clientProfile(business: Int,id: Int) = JsonContracts.clientProfile(fixture("client-$business-$id"))
        override suspend fun taskDetails(business: Int,id: Int): TaskDetails { requests += Triple("task",business,id); return CompletableDeferred<TaskDetails>().also { tasks += it }.await() }
        override suspend fun thread(business: Int,id: Int): InboxThread { requests += Triple("thread",business,id); return CompletableDeferred<InboxThread>().also { threads += it }.await() }
        override suspend fun appointment(business: Int,id: Int): AppointmentDetail { requests += Triple("appointment",business,id); return CompletableDeferred<AppointmentDetail>().also { appointments += it }.await() }
    }
    private fun check(block: suspend TestScope.(ClientProfileViewModel,ClientWorkModel,Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val repo = Controlled(::fixture); val model = ClientProfileViewModel(repo)
        try { model.load(101,701); runCurrent(); block(model,model.work!!,repo) }
        finally { model.clear(); model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun suppliedWindowsRetainOrderAndRejectUnknownDuplicateOverflowOrWrongClient() {
        val p = profile()
        assertEquals((1401..1405).toList(),p.providedTasks!!.map { it.id }); assertEquals(listOf(931,932),p.providedConversations!!.map { it.id })
        assertNull(p.copy(tasks=null).providedTasks); assertTrue(p.copy(tasks=emptyList()).providedTasks!!.isEmpty())
        assertNull(p.copy(conversations=null).providedConversations); assertTrue(p.copy(conversations=emptyList()).providedConversations!!.isEmpty())
        listOf(0,4,6).forEach { assertNull(p.copy(maxRelated=it).providedTasks) }
        assertNull(p.copy(maxRelated=6).providedAppointments)
        assertEquals(listOf(5101),p.providedAppointments!!.map { it.id })
        val t = p.tasks!!.first(); val c = p.conversations!!.first()
        assertNull(p.copy(tasks=listOf(t,t)).providedTasks)
        for (id in listOf(null,0,702)) assertNull(p.copy(tasks=listOf(t.copy(clientID=id))).providedTasks)
        val invalid = p.copy(tasks=listOf(t.copy(clientID=702)))
        assertTrue(invalid.validFor(101,701)); assertNotNull(invalid.providedConversations)
        assertNull(p.copy(conversations=listOf(c,c)).providedConversations)
        assertNull(p.copy(conversations=listOf(c.copy(unreadCount=-1))).providedConversations)
        val json = JSONObject(fixture("client-101-701")); json.getJSONObject("related").remove("tasks")
        assertNull(JsonContracts.clientProfile(json.toString()).providedTasks)
        json.getJSONObject("related").put("tasks",JSONObject.NULL)
        assertNull(JsonContracts.clientProfile(json.toString()).providedTasks)
        json.getJSONObject("related").put("tasks","bad")
        try { JsonContracts.clientProfile(json.toString()); fail() } catch (error: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD,error.problem) }
    }
    @Test fun actualExistingGetRoutesAndChildBackKeepProfileAndOtherModuleQueries() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { r ->
            requests += r; val b = r.query["business"]; val id = r.path.trimEnd('/').substringAfterLast('/')
            val name = when {
                r.path.endsWith("/clients/") -> "clients-$b"
                r.path.contains("/clients/") -> "client-$b-$id"
                r.path.contains("/tasks/") -> "task-$b-$id"
                r.path.contains("/inbox/") -> "inbox-$b-$id"
                else -> "appointment-$b-$id"
            }; ReadResponse(200,fixture(name))
        })
        val model = ClientProfileViewModel(repo); val directory = ClientDirectoryViewModel(repo)
        try {
            directory.load(101); runCurrent(); directory.search("Alpha")
            for ((b,id,task,thread,appointment) in listOf(listOf(101,701,1401,931,5101),listOf(202,801,2401,1031,5201))) {
                model.load(b,id); runCurrent(); val work = model.work!!; val request = work.state.selection!!
                for (target in listOf(ClientWorkTarget.Task(task),ClientWorkTarget.Conversation(thread),ClientWorkTarget.Appointment(appointment))) {
                    work.open(target,request); runCurrent(); assertNotNull(work.state.detail); assertNull(work.state.problem)
                    assertTrue(model.backWork()); assertNull(work.state.detail); assertEquals(id,model.state.detail!!.client.id); assertEquals(request,work.state.selection)
                }
                assertEquals(listOf("/api/mobile/v1/tasks/$task/","/api/mobile/v1/inbox/$thread/","/api/mobile/v1/appointments/$appointment/"),requests.takeLast(3).map { it.path })
                assertEquals(listOf(mapOf("business" to "$b"),mapOf("business" to "$b","limit" to "30"),mapOf("business" to "$b")),requests.takeLast(3).map { it.query })
            }
            assertEquals("Alpha",directory.state.query); assertNull(directory.state.selectedID)
        } finally { model.clear(); model.viewModelScope.cancel(); directory.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun parentRowsNeverGrantAccessOrInferRelationsFromOtherLists() = check { model,work,s ->
        listOf(ClientWorkTarget.Task(1101),ClientWorkTarget.Conversation(901),ClientWorkTarget.Appointment(501)).forEach { work.open(it) }
        runCurrent(); assertTrue(s.requests.isEmpty()); assertNull(work.state.selected)
        work.open(ClientWorkTarget.Task(1401)); runCurrent(); s.tasks[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals(ReadProblem.DENIED,work.state.problem); assertNull(work.state.detail); assertEquals(701,model.state.detail!!.client.id)
        work.open(ClientWorkTarget.Conversation(931)); runCurrent(); s.threads[0].completeExceptionally(ReadException(ReadProblem.NOT_FOUND)); runCurrent()
        assertEquals(ReadProblem.NOT_FOUND,work.state.problem); assertNull(work.state.detail)
        work.open(ClientWorkTarget.Appointment(5101)); runCurrent(); s.appointments[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertNull(work.state.detail); assertEquals(701,model.state.detail!!.client.id)
    }
    @Test fun everyIndependentTargetNeedsCurrentIdentityBusinessAndExplicitClientBacklink() = check { _,work,s ->
        val t = task()
        val invalid = listOf(t.copy(business=202),t.copy(task=t.task.copy(id=1402)),t.copy(task=t.task.copy(clientID=null)),t.copy(task=t.task.copy(clientID=702)))
        invalid.forEachIndexed { index,row -> work.open(ClientWorkTarget.Task(1401)); runCurrent(); s.tasks[index].complete(row); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,work.state.problem); assertNull(work.state.detail) }
        val c = thread()
        listOf(c.copy(clientRefID=null),c.copy(clientRefID=702),c.copy(business=202),c.copy(conversation=c.conversation.copy(id=932))).forEachIndexed { index,row ->
            work.open(ClientWorkTarget.Conversation(931)); runCurrent(); s.threads[index].complete(row); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,work.state.problem); assertNull(work.state.detail)
        }
        val a = appointment()
        listOf(a.copy(clientRefID=702),a.copy(business=202),a.copy(appointment=a.appointment.copy(id=5102))).forEachIndexed { index,row ->
            work.open(ClientWorkTarget.Appointment(5101)); runCurrent(); s.appointments[index].complete(row); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,work.state.problem); assertNull(work.state.detail)
        }
        work.open(ClientWorkTarget.Appointment(5101)); runCurrent(); s.appointments[3].complete(a.copy(appointment=a.appointment.copy(startAt=null,endAt=null))); runCurrent()
        assertNotNull(work.state.detail); assertNull(work.state.problem)
    }
    @Test fun repeatReadAndBackReopenRejectLateSuccessOrErrorAndRetainRedactedHeaders() = check { model,work,s ->
        work.open(ClientWorkTarget.Task(1401)); runCurrent(); work.open(ClientWorkTarget.Task(1401)); runCurrent()
        s.tasks[1].complete(task().copy(task=task().task.copy(title=null))); runCurrent(); s.tasks[0].complete(task()); runCurrent()
        assertNull(work.state.detail!!.title); assertNull(work.state.tasks!!.first().title)
        work.open(ClientWorkTarget.Conversation(931)); runCurrent(); assertTrue(model.backWork())
        work.open(ClientWorkTarget.Conversation(931)); runCurrent(); s.threads[1].complete(thread()); runCurrent(); s.threads[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertNull(work.state.problem); assertNotNull(work.state.detail)
        work.open(ClientWorkTarget.Task(1401)); runCurrent(); model.backWork(); s.tasks[2].complete(task()); runCurrent()
        assertNull(work.state.detail); assertNull(work.state.selected); assertEquals(701,model.state.detail!!.client.id)
    }
    @Test fun parentRefreshOldUiTokenAndBusinessRoundTripInvalidateChildren() = check { model,work,s ->
        val stale = work.state.selection!!
        work.open(ClientWorkTarget.Task(1401),stale); runCurrent(); model.load(101,701); runCurrent()
        s.tasks[0].complete(task()); runCurrent(); assertNull(work.state.detail); assertNotEquals(stale,work.state.selection)
        work.open(ClientWorkTarget.Task(1401),stale); runCurrent(); assertEquals(1,s.requests.size); assertFalse(work.back(stale))
        work.open(ClientWorkTarget.Conversation(931)); runCurrent(); model.load(202,801); runCurrent(); s.threads[0].complete(thread()); runCurrent()
        assertEquals(202,work.state.selection!!.business); assertNull(work.state.detail)
        model.load(101,701); runCurrent(); work.open(ClientWorkTarget.Task(1401),stale); runCurrent(); assertEquals(2,s.requests.size)
        work.open(ClientWorkTarget.Task(1401)); runCurrent(); model.clear(); s.tasks[1].complete(task()); runCurrent()
        assertNull(work.state.parent); assertNull(work.state.tasks); assertNull(work.state.conversations); assertNull(work.state.detail)
    }
    @Test fun cancellationAndOwnerScopeTeardownDoNotLeaveLoadingOrAcceptLateState() = check { model,work,s ->
        work.open(ClientWorkTarget.Task(1401)); runCurrent(); s.tasks[0].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(work.state.loading); assertNull(work.state.selected); assertNotNull(model.state.detail)
        work.open(ClientWorkTarget.Conversation(931)); runCurrent(); model.viewModelScope.cancel(); runCurrent()
        s.threads[0].complete(thread()); runCurrent(); assertNull(work.state.detail); assertNull(work.state.selected)
    }
}
