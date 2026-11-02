package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.NotificationRepository
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.ui.NotificationCenterViewModel
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class NotificationOwnerControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(b:Int)=JsonContracts.notifications(fixture("notifications-$b"))
    private fun target()=JsonContracts.detail(fixture("appointment-101-501"))
    private class Controlled:NotificationRepository {
        val pages=mutableListOf<CompletableDeferred<NotificationPage>>()
        val targets=mutableListOf<CompletableDeferred<AppointmentDetail>>()
        override suspend fun notifications(business:Int)=CompletableDeferred<NotificationPage>().also {pages+=it}.await()
        override suspend fun appointment(business:Int,id:Int)=CompletableDeferred<AppointmentDetail>().also {targets+=it}.await()
    }
    private fun check(block:suspend TestScope.(NotificationCenterViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=NotificationCenterViewModel(source)
        try {block(model,source)} finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sameBusinessEpochRootInvalidatesPendingListWithoutGetOrLateRestore()=check {m,r->
        assertNull(m.control);assertFalse(m.matches(null));m.load(101,1);runCurrent();val pending=m.control!!;m.retryList(pending);runCurrent();assertEquals(1,r.pages.size)
        m.reconcileOwner(101,2);assertNull(m.state.business);assertNull(m.state.scopeEpoch);assertNull(m.control);assertEquals(1,r.pages.size)
        r.pages[0].complete(page(101));runCurrent();assertTrue(m.state.items.isEmpty());assertNull(m.state.business)
        m.load(101,2);runCurrent();r.pages[1].complete(page(101));runCurrent();val current=m.control!!;m.search("Current",current)
        m.search("leak",pending);m.filterCategory("sales",null,pending);m.filterUnread(true,false,pending);m.open(2101,pending);m.retryList(pending);m.openTarget(pending);runCurrent()
        assertEquals("Current",m.state.query);assertNull(m.state.category);assertFalse(m.state.unreadOnly);assertNull(m.state.selectedID);assertEquals(2,r.pages.size);assertTrue(r.targets.isEmpty())
    }
    @Test fun currentFiltersAndCardKeepReadMarkersWhileOldSnapshotsCannotOverwrite()=check {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();val list=m.control!!
        m.search("Alpha",list);m.filterCategory("sales",null,list);m.filterUnread(true,false,list);m.filterCategory("finance",null,list);m.filterUnread(false,false,list)
        assertEquals("sales",m.state.category);assertTrue(m.state.unreadOnly);assertEquals(listOf(2101),m.state.visible.map {it.id});m.open(2102,list);m.open(999,list);assertNull(m.state.selectedID)
        m.open(2101,list);val card=m.control!!;m.close(list);m.search("old",list);assertEquals(2101,m.state.selectedID);assertEquals("Alpha",m.state.query);assertTrue(m.state.selected!!.unread)
        m.close(card);val returned=m.control!!;m.open(2101,list);assertNull(m.state.selectedID);m.open(2101,returned);val newer=m.control!!;m.close(card);assertEquals(newer,m.control);assertEquals(2101,m.state.selectedID);assertEquals(1,r.pages.size);assertTrue(r.targets.isEmpty())
    }
    @Test fun targetVisitGenerationDeniedBackAndEpochRejectOldCallbacksAndResponses()=check {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();m.open(2101,m.control);val card=m.control!!;val markers=m.state.items.map {it.readAt}
        m.openTarget(card);runCurrent();val first=m.control!!;m.openTarget(first);m.backTarget(card);m.close(card);m.retryList(first);runCurrent();assertEquals(1,r.targets.size);assertTrue(m.state.targetLoading)
        r.targets[0].complete(target());runCurrent();assertEquals(501,m.state.target!!.appointment.id);assertEquals(markers,m.state.items.map {it.readAt});assertTrue(m.state.selected!!.unread)
        m.backTarget(first);assertEquals(2101,m.state.selectedID);assertFalse(m.state.targetActive);val returned=m.control!!;m.openTarget(returned);runCurrent();m.backTarget(first);m.close(returned);m.openTarget(card);runCurrent();assertEquals(2,r.targets.size);assertTrue(m.state.targetLoading)
        r.targets[1].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(m.state.target);assertEquals(ReadProblem.DENIED,m.state.targetProblem)
        m.openTarget(m.control);runCurrent();val old=m.control!!;m.reconcileOwner(101,2);r.targets[2].complete(target());runCurrent();assertNull(m.state.target);assertNull(m.state.business)
        m.load(202,3);runCurrent();r.pages[1].complete(page(202));runCurrent();m.openTarget(old);m.close(old);m.search("old",old);runCurrent();assertEquals(listOf(2201),m.state.items.map {it.id});assertEquals("",m.state.query);assertEquals(3,r.targets.size)
    }
    @Test fun legacyLeadPathNeverBecomesAppointmentAndOldCardCannotCloseNewSelection()=check {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();m.open(2102,m.control);val legacy=m.control!!;m.openTarget(legacy);runCurrent();assertTrue(r.targets.isEmpty());assertFalse(m.state.targetActive)
        m.close(legacy);m.open(2101,m.control);val current=m.control!!;m.close(legacy);m.backTarget(legacy);assertEquals(current,m.control);assertEquals(2101,m.state.selectedID)
        m.close(current);val before=m.control!!;m.retryList(before);runCurrent();m.reconcileOwner(101,2);r.pages[1].complete(page(101));runCurrent();assertNull(m.state.business);assertTrue(m.state.items.isEmpty());m.retryList(before);runCurrent();assertEquals(2,r.pages.size)
    }
}
