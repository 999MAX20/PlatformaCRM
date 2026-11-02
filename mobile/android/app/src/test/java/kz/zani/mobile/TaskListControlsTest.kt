package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.TaskListViewModel
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskListControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(b:Int)=JsonContracts.tasks(fixture("tasks-$b"))
    private fun detail()=JsonContracts.taskDetails(fixture("task-101-1101"))
    private class Controlled:TaskReadRepository {
        val pages=mutableListOf<CompletableDeferred<TaskPage>>()
        val details=mutableListOf<CompletableDeferred<TaskDetails>>()
        override suspend fun tasks(business:Int)=CompletableDeferred<TaskPage>().also {pages+=it}.await()
        override suspend fun taskDetails(business:Int,id:Int)=CompletableDeferred<TaskDetails>().also {details+=it}.await()
    }
    private fun check(block:suspend TestScope.(TaskListViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source)
        try {block(model,source)} finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pendingAndFilteredRowsUseCurrentListAndPreviousStatusSnapshot()=check {m,r->
        assertNull(m.control);assertFalse(m.matches(null));m.load(101,1);runCurrent();val pending=m.control!!
        m.search("pending",pending);m.filterStatus("done",null,pending);m.retryList(pending);runCurrent();assertEquals(1,r.pages.size);assertEquals("",m.state.query);assertNull(m.state.status)
        r.pages[0].complete(page(101));runCurrent();val list=m.control!!;m.search("Alpha",list);m.filterStatus("open",null,list);m.filterStatus("done",null,list)
        assertEquals(listOf(1101),m.state.visible.map {it.id});assertEquals("open",m.state.status);m.open(1102,list);m.open(999,list);runCurrent();assertTrue(r.details.isEmpty());assertNull(m.state.selectedID)
        m.open(1101,list);runCurrent();val card=m.control!!;m.search("old",list);m.filterStatus(null,"open",list);m.retryList(list);m.open(1101,list);runCurrent()
        assertEquals(1,r.pages.size);assertEquals(1,r.details.size);assertEquals(card,m.control);assertEquals("Alpha",m.state.query);assertEquals("open",m.state.status)
        r.details[0].complete(detail());runCurrent();assertEquals(1101,m.state.detail!!.task.id)
    }
    @Test fun backReopenAndOldDetailRetryCannotOperateOnCurrentVisit()=check {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();val list=m.control!!;m.open(1101,list);runCurrent();r.details[0].complete(detail());runCurrent();val old=m.detailSelection!!
        m.back(old);val returned=m.control!!;m.open(1101,list);runCurrent();assertNull(m.state.selectedID);assertEquals(1,r.details.size)
        m.open(1101,returned);runCurrent();val newer=m.detailSelection!!;m.back(old);m.retryDetail(old);m.open(1102,returned);runCurrent()
        assertEquals(2,r.details.size);assertEquals(newer,m.detailSelection);assertTrue(m.state.detailLoading);r.details[1].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,m.state.detailProblem);assertNull(m.state.detail)
        m.back(newer);val before=m.control!!;m.retryList(before);runCurrent();m.retryList(before);runCurrent();assertEquals(2,r.pages.size);r.pages[1].complete(page(101));runCurrent()
    }
    @Test fun ownerEpochRootClearsWithoutGetAndLateRepliesOldCallbacksStayHidden()=check {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();val old=m.control!!;m.retryList(old);runCurrent();m.reconcileCommentOwner(101,2);assertNull(m.control);assertTrue(m.state.items.isEmpty());assertEquals(2,r.pages.size)
        r.pages[1].complete(page(101));runCurrent();assertNull(m.state.business);m.load(101,2);runCurrent();r.pages[2].complete(page(101));runCurrent();val fresh=m.control!!;m.search("Current",fresh)
        m.search("old",old);m.filterStatus("done",null,old);m.open(1101,old);m.retryList(old);runCurrent();assertEquals("Current",m.state.query);assertNull(m.state.status);assertNull(m.state.selectedID);assertEquals(3,r.pages.size);assertTrue(r.details.isEmpty())
        m.load(202,3);runCurrent();r.pages[3].complete(page(202));runCurrent();m.search("old",fresh);m.open(1201,fresh);m.retryList(fresh);runCurrent();assertEquals(listOf(1201),m.state.items.map {it.id});assertEquals("",m.state.query);assertEquals(4,r.pages.size);assertTrue(r.details.isEmpty())
    }
    @Test fun querySourceFilterStillUsesExactContractAndOldListCannotTriggerRead()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {request->
            requests+=request;val business=request.query.getValue("business").toInt()
            FixtureTaskQueries.response(fixture("task-query-source-$business"),business,request.query)
        })
        val model=TaskListViewModel(repo)
        try {
            model.load(101,10);runCurrent();val control=model.control!!;val query=model.querySelection!!;model.filterStatus("done",null,control);assertNull(model.state.status);assertEquals(TaskQueryFilter(),model.state.appliedFilter)
            val filter=TaskQueryFilter("open",TaskDueFilter.TODAY);model.applyFilter(filter,query);runCurrent();model.open(1101,control);model.retryList(control);runCurrent()
            assertEquals(2,requests.size);assertEquals(filter.query(101),requests.last().query);assertEquals(listOf(3165,1101),model.state.items.map {it.id});assertNull(model.state.selectedID)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
