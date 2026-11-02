package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.AttentionQueueViewModel
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AttentionOwnerControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(b:Int=101)=JsonContracts.actions(fixture("actions-$b"))
    private fun task()=JsonContracts.taskDetails(fixture("task-101-1111"))
    private fun appointment()=JsonContracts.detail(fixture("appointment-101-511"))
    private class Controlled:AttentionRepository {
        val pages=mutableListOf<CompletableDeferred<AttentionPage>>()
        val details=mutableListOf<CompletableDeferred<AttentionDetail>>()
        val targets=mutableListOf<Triple<Int,AttentionKind,Int>>()
        override suspend fun actions(business:Int)=CompletableDeferred<AttentionPage>().also {pages+=it}.await()
        private suspend fun target(b:Int,k:AttentionKind,id:Int):AttentionDetail {targets+=Triple(b,k,id);return CompletableDeferred<AttentionDetail>().also {details+=it}.await()}
        override suspend fun taskDetails(business:Int,id:Int)=(target(business,AttentionKind.TASK,id) as AttentionDetail.TaskRead).value
        override suspend fun thread(business:Int,id:Int)=(target(business,AttentionKind.CONVERSATION,id) as AttentionDetail.ThreadRead).value
        override suspend fun appointment(business:Int,id:Int)=(target(business,AttentionKind.APPOINTMENT,id) as AttentionDetail.AppointmentRead).value
    }
    private fun check(block:suspend TestScope.(AttentionQueueViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=AttentionQueueViewModel(r)
        try {block(m,r)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun currentFilteredCompositeRowIsRequiredAndPendingCallbacksDoNotRepeatGet()=check {m,r->
        assertNull(m.control);assertFalse(m.matches(null));m.load(101,1);runCurrent();val pending=m.control!!;m.search("old",pending);m.retryList(pending);runCurrent();assertEquals("",m.state.query);assertEquals(1,r.pages.size)
        val a=page();r.pages[0].complete(a);runCurrent();val list=m.control!!;m.search("follow-up",list);m.open(a.items[4].identity,list);m.open(a.items[0].identity,list);runCurrent();assertTrue(r.details.isEmpty())
        m.open(a.items[1].identity,list);runCurrent();val card=m.control!!;m.search("old",list);m.retryList(list);m.open(a.items[1].identity,list);m.back(list);m.retryDetail(card);runCurrent();assertEquals(1,r.details.size);assertEquals(1,r.pages.size);assertEquals("follow-up",m.state.query)
        r.details[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,m.state.detailProblem);assertNull(m.state.detail)
    }
    @Test fun oldBackRetryAndRowCannotChangeNewVisitAndLegacyLeadDoesNotBecomeAppointment()=check {m,r->
        val a=page();m.load(101,1);runCurrent();r.pages[0].complete(a);runCurrent();val list=m.control!!;m.open(a.items[1].identity,list);runCurrent();val first=m.control!!;r.details[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent()
        m.retryDetail(first);runCurrent();val newer=m.control!!;m.back(first);m.retryDetail(first);runCurrent();assertEquals(2,r.details.size);assertEquals(newer,m.control);r.details[1].complete(AttentionDetail.TaskRead(task()));runCurrent();m.back(newer);val returned=m.control!!
        m.open(a.items[1].identity,list);runCurrent();assertNull(m.state.selectedID);m.open(a.items[3].identity,returned);runCurrent();assertEquals(2,r.details.size);m.open(a.items[4].identity,returned);runCurrent();assertEquals(Triple(101,AttentionKind.APPOINTMENT,511),r.targets.last());r.details[2].complete(AttentionDetail.AppointmentRead(appointment()));runCurrent()
    }
    @Test fun rootSameBusinessEpochInvalidatesPendingTargetAndOldCallbacksWithoutGet()=check {m,r->
        val a=page();m.load(101,1);runCurrent();r.pages[0].complete(a);runCurrent();val old=m.control!!;m.open(a.items[4].identity,old);runCurrent();val card=m.control!!;m.reconcileOwner(101,2)
        assertNull(m.control);assertTrue(m.state.items.isEmpty());assertNull(m.state.detail);assertEquals(1,r.pages.size);assertEquals(1,r.details.size);r.details[0].complete(AttentionDetail.AppointmentRead(appointment()));runCurrent();assertNull(m.state.detail);assertNull(m.state.business)
        m.load(101,2);runCurrent();r.pages[1].complete(a);runCurrent();val fresh=m.control!!;m.search("Current",fresh);m.search("leak",old);m.retryList(old);m.open(a.items[1].identity,old);m.retryDetail(card);m.back(card);runCurrent();assertEquals("Current",m.state.query);assertNull(m.state.selectedID);assertEquals(2,r.pages.size);assertEquals(1,r.details.size)
        m.load(202,3);runCurrent();r.pages[2].complete(page(202));runCurrent();m.search("old",fresh);m.retryList(fresh);m.open(page(202).items[0].identity,fresh);runCurrent();assertEquals(202,m.state.business);assertEquals("",m.state.query);assertEquals(3,r.pages.size);assertEquals(1,r.details.size)
    }
    @Test fun lateOldEpochListCannotRepopulateAndInvalidExplicitEpochDoesNotFetch()=check {m,r->
        m.load(101,0);runCurrent();assertNull(m.control);assertEquals(ReadProblem.INVALID_CONTEXT,m.state.problem);assertTrue(r.pages.isEmpty());m.load(101,1);runCurrent();val old=m.control!!;m.reconcileOwner(101,2);r.pages[0].complete(page());runCurrent();assertTrue(m.state.items.isEmpty());assertNull(m.state.business)
        m.retryList(old);runCurrent();assertEquals(1,r.pages.size);m.load(101,2);runCurrent();r.pages[1].complete(page());runCurrent();val current=m.control!!;m.retryList(current);runCurrent();m.retryList(current);runCurrent();assertEquals(3,r.pages.size);r.pages[2].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(m.state.detail);assertEquals(ReadProblem.DENIED,m.state.problem);assertFalse(m.state.showsEmpty)
    }
}
