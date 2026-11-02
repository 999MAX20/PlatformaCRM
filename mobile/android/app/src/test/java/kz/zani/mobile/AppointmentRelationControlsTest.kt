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
class AppointmentRelationControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun profile()=JsonContracts.clientProfile(fixture("client-101-7001"))
    private fun task()=JsonContracts.taskDetails(fixture("task-101-1301"))
    private inner class Controlled:AgendaRepository,AppointmentRelatedRepository {
        val profiles=mutableListOf<CompletableDeferred<ClientProfile>>();val tasks=mutableListOf<CompletableDeferred<TaskDetails>>()
        override suspend fun bootstrap()=JsonContracts.bootstrap(fixture("bootstrap"))
        override suspend fun appointments(business:Int,day:String)=JsonContracts.appointments(fixture("appointments-$business"))
        override suspend fun appointment(business:Int,id:Int)=JsonContracts.detail(fixture("appointment-$business-$id"))
        override suspend fun clientProfile(business:Int,id:Int)=CompletableDeferred<ClientProfile>().also {profiles+=it}.await()
        override suspend fun taskDetails(business:Int,id:Int)=CompletableDeferred<TaskDetails>().also {tasks+=it}.await()
    }
    private fun check(block:suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val links=AppointmentRelationsViewModel(r);val m=AgendaViewModel(r,initialDay={"2026-10-28"},relations=links)
        try {m.start();runCurrent();m.openDetail(501,m.control);runCurrent();block(m,links,r)} finally {links.clear();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun clientPendingAndRetryHaveSeparateVisitAndKeepParent()=check {m,l,r->
        val parent=m.control;val notes=m.state.detail!!.notes;val entry=l.presentation!!;l.openClient(presentation=entry);runCurrent();val first=l.presentation!!;l.openClient(presentation=entry);l.openTask(1301,presentation=entry);l.retry(first);l.back(entry);runCurrent();assertEquals(1,r.profiles.size);assertTrue(r.tasks.isEmpty())
        r.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,l.profile.state.problem);l.retry(first);runCurrent();val newer=l.presentation!!;l.back(first);l.retry(first);runCurrent();assertEquals(2,r.profiles.size);r.profiles[1].complete(profile());runCurrent();assertEquals(newer,l.presentation);assertEquals(7001,l.profile.state.detail!!.client.id);assertEquals(parent,m.control);assertEquals(notes,m.state.detail!!.notes)
    }
    @Test fun sameTaskReopenRejectsOldBackRetryAndLateError()=check {m,l,r->
        val parent=m.control;l.openTask(1301,presentation=l.presentation);runCurrent();val old=l.presentation!!;l.back(old);l.openTask(1301,presentation=l.presentation);runCurrent();val fresh=l.presentation!!;l.back(old);l.retry(old);runCurrent();assertEquals(2,r.tasks.size);r.tasks[1].complete(task());runCurrent();r.tasks[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(fresh,l.presentation);assertEquals(1301,l.state.task!!.task.id);assertNull(l.state.problem);assertEquals(parent,m.control)
    }
    @Test fun parentRefreshInvalidatesPendingChildAndOldParentEntry()=check {m,l,r->
        l.openClient(presentation=l.presentation);runCurrent();val old=l.presentation!!;val parent=m.control;m.retryDetail(parent);runCurrent();val newParent=l.presentation!!;r.profiles[0].complete(profile());runCurrent();l.openClient(presentation=old);l.openTask(1301,presentation=old);l.back(old);l.retry(old);runCurrent();assertEquals(1,r.profiles.size);assertTrue(r.tasks.isEmpty());assertEquals(newParent,l.presentation);assertNull(l.state.selected);assertNull(l.profile.state.detail);assertNotEquals(parent.detail,m.control.detail)
    }
    @Test fun unknownTaskAndAmbiguousClientDoNotFetchAndTaskForeignKeyStillValidates()=check {_,l,r->
        val request=l.state.request!!;l.bind(l.state.parent!!.copy(clientRefID=7002),request);val entry=l.presentation!!;l.openClient(presentation=entry);l.openTask(999,presentation=entry);runCurrent();assertTrue(r.profiles.isEmpty());assertTrue(r.tasks.isEmpty());l.openTask(1301,presentation=entry);runCurrent()
        val j=JSONObject(fixture("task-101-1301"));j.getJSONObject("details").put("appointment_id",502);r.tasks[0].complete(JsonContracts.taskDetails(j.toString()));runCurrent();assertNull(l.state.task);assertEquals(ReadProblem.INVALID_PAYLOAD,l.state.problem);assertEquals(1,r.tasks.size)
    }
}
