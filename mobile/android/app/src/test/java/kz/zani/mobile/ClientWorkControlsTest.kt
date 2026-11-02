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
class ClientWorkControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private inner class Controlled:ClientProfileRepository,ClientWorkRepository {
        val tasks=mutableListOf<CompletableDeferred<TaskDetails>>();val threads=mutableListOf<CompletableDeferred<InboxThread>>();val appointments=mutableListOf<CompletableDeferred<AppointmentDetail>>()
        val requests=mutableListOf<Triple<String,Int,Int>>()
        override suspend fun clientProfile(business:Int,id:Int)=JsonContracts.clientProfile(fixture("client-$business-$id"))
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {requests+=Triple("task",business,id);return CompletableDeferred<TaskDetails>().also {tasks+=it}.await()}
        override suspend fun thread(business:Int,id:Int):InboxThread {requests+=Triple("thread",business,id);return CompletableDeferred<InboxThread>().also {threads+=it}.await()}
        override suspend fun appointment(business:Int,id:Int):AppointmentDetail {requests+=Triple("appointment",business,id);return CompletableDeferred<AppointmentDetail>().also {appointments+=it}.await()}
    }
    private fun check(block:suspend TestScope.(ClientProfileViewModel,ClientWorkModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=ClientProfileViewModel(r)
        try {m.loadScoped(101,701,1);runCurrent();block(m,m.work!!,r)} finally {m.clear();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun entryRequiresCurrentProvidedWindowAndPendingVisitCannotRepeatOrSwitch()=check {m,w,r->
        assertFalse(w.matches(null));val entry=w.presentation!!;val read=m.readSelection;w.open(ClientWorkTarget.Task(1101),presentation=entry);w.open(ClientWorkTarget.Conversation(901),presentation=entry);w.open(ClientWorkTarget.Appointment(501),presentation=entry);runCurrent();assertTrue(r.requests.isEmpty())
        w.open(ClientWorkTarget.Task(1401),presentation=entry);runCurrent();val child=w.presentation!!;w.open(ClientWorkTarget.Task(1401),presentation=entry);w.open(ClientWorkTarget.Conversation(931),presentation=entry);w.retry(child);assertFalse(w.back(presentation=entry));runCurrent();assertEquals(1,r.requests.size);assertEquals(read,m.readSelection);assertEquals(ClientWorkTarget.Task(1401),w.state.selected)
        r.tasks[0].complete(JsonContracts.taskDetails(fixture("task-101-1401")));runCurrent()
    }
    @Test fun eachTypedChildDenialThenCapturedRetryPreservesParentAndCaps()=check {m,w,r->
        val read=m.readSelection;val notes=m.state.detail!!.notes;val windows=Triple(w.state.tasks!!.size,w.state.conversations!!.size,w.state.appointments!!.size)
        val targets=listOf(ClientWorkTarget.Task(1401),ClientWorkTarget.Conversation(931),ClientWorkTarget.Appointment(5101))
        for(target in targets) {
            w.open(target,presentation=w.presentation);runCurrent();val old=w.presentation!!
            when(target) {is ClientWorkTarget.Task->r.tasks.last().completeExceptionally(ReadException(ReadProblem.DENIED));is ClientWorkTarget.Conversation->r.threads.last().completeExceptionally(ReadException(ReadProblem.DENIED));is ClientWorkTarget.Appointment->r.appointments.last().completeExceptionally(ReadException(ReadProblem.DENIED))};runCurrent()
            assertEquals(ReadProblem.DENIED,w.state.problem);assertNull(w.state.detail);w.retry(old);runCurrent();val fresh=w.presentation!!;assertFalse(w.back(presentation=old));w.retry(old);runCurrent()
            when(target) {is ClientWorkTarget.Task->r.tasks.last().complete(JsonContracts.taskDetails(fixture("task-101-1401")));is ClientWorkTarget.Conversation->r.threads.last().complete(JsonContracts.thread(fixture("inbox-101-931")));is ClientWorkTarget.Appointment->r.appointments.last().complete(JsonContracts.detail(fixture("appointment-101-5101")))};runCurrent()
            assertEquals(fresh,w.presentation);assertNotNull(w.state.detail);assertNull(w.state.problem);assertTrue(w.back(presentation=fresh));assertEquals(read,m.readSelection);assertEquals(notes,m.state.detail!!.notes);assertEquals(windows,Triple(w.state.tasks!!.size,w.state.conversations!!.size,w.state.appointments!!.size))
        }
        assertEquals(6,r.requests.size)
    }
    @Test fun staleProfileReturnNeverMeansNoChildOrClosesReopenedCurrentVisit()=check {m,w,r->
        val parent=m.workReturnControl;assertEquals(ClientWorkBack.NO_CHILD,m.backWork(parent));w.open(ClientWorkTarget.Task(1401),presentation=w.presentation);runCurrent();val oldReturn=m.workReturnControl;val old=w.presentation!!
        assertEquals(ClientWorkBack.STALE,m.backWork(parent));assertEquals(ClientWorkBack.CLOSED,m.backWork(oldReturn));w.open(ClientWorkTarget.Task(1401),presentation=w.presentation);runCurrent();val fresh=m.workReturnControl
        assertEquals(ClientWorkBack.STALE,m.backWork(oldReturn));assertFalse(w.back(presentation=old));w.retry(old);runCurrent();assertEquals(2,r.tasks.size);assertEquals(fresh,m.workReturnControl)
        val j=JSONObject(fixture("task-101-1401"));j.getJSONObject("task").put("title",JSONObject.NULL);r.tasks[1].complete(JsonContracts.taskDetails(j.toString()));runCurrent();r.tasks[0].complete(JsonContracts.taskDetails(fixture("task-101-1401")));runCurrent();assertNull(w.state.detail!!.title);assertEquals(701,m.state.detail!!.client.id);assertEquals(fresh,m.workReturnControl)
    }
    @Test fun parentReloadAndEpochChangeRevokePendingResultAndOldReturnToken()=check {m,w,r->
        val oldRead=m.readSelection;w.open(ClientWorkTarget.Conversation(931),presentation=w.presentation);runCurrent();val old=w.presentation!!;val oldReturn=m.workReturnControl;m.loadScoped(101,701,2);runCurrent();r.threads[0].complete(JsonContracts.thread(fixture("inbox-101-931")));runCurrent()
        assertNull(w.state.selected);assertNull(w.state.detail);assertNotEquals(oldRead,m.readSelection);assertEquals(2,m.state.scopeEpoch);assertEquals(ClientWorkBack.STALE,m.backWork(oldReturn));w.open(ClientWorkTarget.Task(1401),presentation=old);w.retry(old);runCurrent();assertEquals(1,r.requests.size);assertEquals(ClientWorkBack.NO_CHILD,m.backWork(m.workReturnControl))
    }
    @Test fun typedWrapperStillRejectsWrongIndependentClientForeignKey()=check {m,w,r->
        w.open(ClientWorkTarget.Task(1401),presentation=w.presentation);runCurrent();val j=JSONObject(fixture("task-101-1401"));j.getJSONObject("task").put("client_id",702);r.tasks[0].complete(JsonContracts.taskDetails(j.toString()));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,w.state.problem);assertNull(w.state.detail);assertEquals(701,m.state.detail!!.client.id);assertEquals(1,r.requests.size)
    }
    @Test fun childCancellationKeepsParentAndClearMakesOldControlsInert()=check {m,w,r->
        w.open(ClientWorkTarget.Appointment(5101),presentation=w.presentation);runCurrent();val old=w.presentation!!;val parent=m.readSelection;r.appointments[0].cancel();runCurrent();assertNull(w.state.selected);assertNull(w.state.detail);assertFalse(w.state.loading);assertEquals(parent,m.readSelection);w.retry(old);runCurrent();assertEquals(1,r.requests.size)
        val beforeClear=m.workReturnControl;m.clear();assertEquals(ClientWorkBack.STALE,m.backWork(beforeClear));assertNull(w.presentation);w.open(ClientWorkTarget.Task(1401),presentation=old);runCurrent();assertEquals(1,r.requests.size)
    }
}
