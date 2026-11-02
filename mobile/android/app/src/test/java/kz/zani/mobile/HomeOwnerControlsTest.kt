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
class HomeOwnerControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun home(b:Int=101)=JsonContracts.home(fixture("home-$b"))
    private fun today(b:Int=101)=JsonContracts.today(fixture("today-$b"))
    private class Controlled:HomeTodayRepository {
        val homes=mutableListOf<CompletableDeferred<HomeSummary>>()
        val days=mutableListOf<CompletableDeferred<TodaySummary>>()
        override suspend fun home(business:Int)=CompletableDeferred<HomeSummary>().also {homes+=it}.await()
        override suspend fun today(business:Int,day:String)=CompletableDeferred<TodaySummary>().also {days+=it}.await()
    }
    private fun check(block:suspend TestScope.(HomeTodayViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=HomeTodayViewModel(r)
        try {block(m,r)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pendingAndOldSectionCallbacksDoNotDuplicateIndependentRetries()=check {m,r->
        assertNull(m.owner);assertNull(m.homeControl);assertFalse(m.matches(null));m.start(101,"2026-10-28",1);runCurrent()
        m.reloadHome(m.homeControl);m.reloadToday(m.todayControl);runCurrent();assertEquals(1,r.homes.size);assertEquals(1,r.days.size)
        r.homes[0].complete(home());r.days[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNotNull(m.state.home);assertNull(m.state.today)
        val h=m.homeControl!!;val t=m.todayControl!!;m.reloadToday(t);m.reloadHome(h);runCurrent();m.reloadToday(m.todayControl);m.reloadHome(m.homeControl);runCurrent();assertEquals(2,r.homes.size);assertEquals(2,r.days.size)
        r.homes[1].complete(home());r.days[1].complete(today());runCurrent();m.reloadHome(h);m.reloadToday(t);m.reloadHome(m.todayControl);runCurrent();assertEquals(2,r.homes.size);assertEquals(2,r.days.size);assertNotNull(m.state.home);assertNotNull(m.state.today)
    }
    @Test fun navigationIsConsumedOnceAndOldBackCannotCloseNewChildOrUsePreChildRetry()=check {m,r->
        m.start(101,"2026-10-28",1);runCurrent();r.homes[0].complete(home());r.days[0].complete(today());runCurrent()
        val section=m.homeControl!!;val before=m.navigationControl!!;m.open(HomeDestination.TASKS,before);val tasks=m.navigationControl!!
        assertNull(m.takeNavigation(before));assertEquals(HomeDestination.TASKS,m.takeNavigation(tasks));assertNull(m.takeNavigation(tasks));assertEquals(HomeDestination.TASKS,m.state.destination)
        m.open(HomeDestination.INBOX,before);m.back(before);assertEquals(HomeDestination.TASKS,m.state.destination);m.back(tasks)
        m.open(HomeDestination.CLIENTS,m.navigationControl);val clients=m.navigationControl!!;m.back(tasks);assertEquals(HomeDestination.CLIENTS,m.state.destination);assertEquals(HomeDestination.CLIENTS,m.takeNavigation(clients));assertNull(m.takeNavigation(clients))
        m.back(clients);m.reloadHome(section);runCurrent();assertEquals(1,r.homes.size);assertNotNull(m.state.home);assertNotNull(m.state.today)
    }
    @Test fun rootEpochClearWithoutGetRejectsLateSummaryAndDayBusinessCallbacks()=check {m,r->
        m.start(101,"2026-10-28",1);runCurrent();r.homes[0].complete(home());r.days[0].complete(today());runCurrent();val old=m.homeControl!!;val oldNav=m.navigationControl!!;val oldDay=m.todayControl!!
        m.reloadHome(old);runCurrent();m.reconcileOwner(101,2);assertNull(m.owner);assertNull(m.state.home);assertNull(m.state.today);assertEquals(2,r.homes.size);assertEquals(1,r.days.size)
        m.start(101,"2026-10-28",2);runCurrent();val hidden=JsonContracts.home(JSONObject(fixture("home-101")).put("sections",JSONObject()).toString());r.homes[2].complete(hidden);r.days[1].complete(today());runCurrent();r.homes[1].complete(home());runCurrent()
        m.reloadHome(old);m.reloadToday(oldDay);m.open(HomeDestination.TASKS,oldNav);runCurrent();assertEquals(3,r.homes.size);assertEquals(2,r.days.size);assertNull(m.state.home!!.tasks);assertNull(m.state.destination);assertEquals(2,m.owner!!.epoch)
        val previous=m.todayControl!!;m.start(101,"2026-10-29",2);runCurrent();r.homes[3].complete(home());r.days[2].complete(today());runCurrent();m.reloadToday(previous);runCurrent();assertNull(m.state.today);assertEquals(ReadProblem.INVALID_PAYLOAD,m.state.todayProblem);assertEquals(3,r.days.size)
        m.start(202,"2026-10-28",3);runCurrent();r.homes[4].complete(home(202));r.days[3].complete(today(202));runCurrent();m.open(HomeDestination.INBOX,m.navigationControl);m.back(oldNav);m.reloadHome(old);runCurrent();assertEquals(HomeDestination.INBOX,m.state.destination);assertEquals(202,m.state.home!!.business);assertEquals(202,m.state.today!!.business);assertEquals(5,r.homes.size)
    }
    @Test fun missingOrInvalidExplicitEpochCannotCreateUiControlsWhileLegacyApiRemains()=check {m,r->
        m.start(101,"2026-10-28",0);runCurrent();assertNull(m.owner);assertEquals(ReadProblem.INVALID_CONTEXT,m.state.homeProblem);assertTrue(r.homes.isEmpty());assertTrue(r.days.isEmpty())
        m.start(101,"2026-10-28");runCurrent();assertNull(m.owner);assertNull(m.navigationControl);m.open(HomeDestination.TASKS,null);assertNull(m.state.destination)
        m.open(HomeDestination.TASKS);assertEquals(HomeDestination.TASKS,m.takeNavigation());assertEquals(1,r.homes.size);assertEquals(1,r.days.size)
    }
}
