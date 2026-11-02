package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.junit.Assert.*
import org.junit.Test
import java.net.URI

@OptIn(ExperimentalCoroutinesApi::class)
class TaskQueryTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun response(request: ReadRequest): ReadResponse {
        val business=request.query.getValue("business").toInt();val id=if(request.path.endsWith("tasks/"))null else request.path.trimEnd('/').substringAfterLast('/').toInt()
        return FixtureTaskQueries.response(fixture("task-query-source-$business"),business,request.query,id)
    }
    private fun repository(requests: MutableList<ReadRequest> = mutableListOf())=APIReadRepository(ReadTransport {r->requests+=r;response(r)})
    @Test fun exactWireQuerySourceCountsIntersectionAndClockDoNotUseDeviceBusinessCalendar()=runTest {
        val requests=mutableListOf<ReadRequest>();val repo=repository(requests)
        for(business in listOf(101,202)) {
            val all=repo.tasks(business,TaskQueryFilter());assertEquals(if(business==101)73 else 71,all.total);assertEquals(50,all.items.size)
            val overdue=repo.tasks(business,TaskQueryFilter(due=TaskDueFilter.OVERDUE));assertEquals(66,overdue.total);assertEquals(50,overdue.items.size);assertTrue(overdue.items.none {it.status in listOf("done","cancelled")})
            val today=repo.tasks(business,TaskQueryFilter(due=TaskDueFilter.TODAY));val start=if(business==101)3100 else 4100
            assertEquals(if(business==101)6 else 5,today.total);assertTrue(today.items.any {it.id==start+66});assertTrue(today.items.any {it.id==start+67})
            assertTrue(today.items.none {it.id==start});assertTrue(today.items.any {it.id==start+68})
            val open=repo.tasks(business,TaskQueryFilter("open",TaskDueFilter.TODAY));assertEquals(2,open.total);assertTrue(open.items.all {it.status=="open"})
            val empty=repo.tasks(business,TaskQueryFilter("done",TaskDueFilter.OVERDUE));assertEquals(0,empty.total);assertTrue(empty.items.isEmpty())
            val row=overdue.items[0];assertEquals(row,repo.taskDetails(business,row.id).task)
        }
        assertEquals(ReadRequest("/api/mobile/v1/tasks/",mapOf("business" to "101","limit" to "50")),requests[0])
        assertEquals(mapOf("business" to "101","limit" to "50","status" to "open","due" to "today"),requests[3].query)
        val descriptor=NativeRequestBuilder(URI("https://fixtures.invalid"),30000).request(requests[3]);assertEquals("GET",descriptor.method);assertEquals("business=101&due=today&limit=50&status=open",descriptor.uri.rawQuery)
    }
    @Test fun noWebAliasesCursorSearchOrExtraPolicyAreInvented() {
        val data=fixture("task-query-source-101")
        listOf("past","future","none","upcoming").forEach {assertEquals(400,FixtureTaskQueries.response(data,101,mapOf("business" to "101","limit" to "50","due" to it)).status)}
        listOf("search","cursor").forEach {assertEquals(400,FixtureTaskQueries.response(data,101,mapOf("business" to "101","limit" to "50",it to "value")).status)}
        val active=FixtureTaskQueries.response(data,101,mapOf("business" to "101","limit" to "50","status" to "active"));assertEquals(0,JsonContracts.tasks(active.body).total)
        assertEquals(mapOf("business" to "101","limit" to "50"),TaskQueryFilter("").query(101))
    }
    @Test fun actualListSelectBackRefreshClearRetainsQueryAndManualCommentWithoutWrites()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=repository(requests)
        val comments=object: TaskCommentDraftSource {override suspend fun matchesFixture(detail: TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,JsonContracts.taskDetails(fixture("task-${detail.business}-${detail.task.id}")))}
        val model=TaskListViewModel(repo,comments)
        try {
            model.load(101,10);runCurrent();assertTrue(model.state.partial);val initial=model.querySelection!!
            val filter=TaskQueryFilter("open",TaskDueFilter.TODAY);model.applyFilter(filter,initial);runCurrent();assertEquals(listOf(3165,1101),model.state.items.map {it.id});assertEquals(2,model.state.total)
            val query=model.querySelection!!;model.open(1101);runCurrent();val target=model.detailSelection!!;val comment=model.comment!!;comment.open(comment.state.read!!);comment.update("Keep own comment",comment.state.selection!!)
            model.back(target);assertEquals(filter,model.state.appliedFilter);model.refreshFilter(query);runCurrent();assertEquals(filter.query(101),requests.last().query)
            model.open(1101);runCurrent();assertEquals("Keep own comment",comment.state.text)
            val fresh=model.detailSelection;val count=requests.size;model.back(target);model.retryDetail(target);model.applyFilter(TaskQueryFilter(),initial);model.refreshFilter(initial);runCurrent()
            assertEquals(fresh,model.detailSelection);assertEquals(count,requests.size)
            model.back(fresh);model.applyFilter(TaskQueryFilter("done",TaskDueFilter.OVERDUE),model.querySelection);runCurrent();assertTrue(model.state.showsEmpty);assertFalse(model.state.partial);assertFalse(comment.state.available)
            model.applyFilter(TaskQueryFilter(),model.querySelection);runCurrent();assertEquals(73,model.state.total);assertTrue(model.state.partial)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class Controlled: TaskQueryRepository {
        val pending=mutableListOf<CompletableDeferred<TaskPage>>();val filters=mutableListOf<TaskQueryFilter>()
        override suspend fun tasks(business: Int)=tasks(business,TaskQueryFilter())
        override suspend fun tasks(business: Int,filter: TaskQueryFilter)=CompletableDeferred<TaskPage>().also {pending+=it;filters+=filter}.await()
        override suspend fun taskDetails(business: Int,id: Int): TaskDetails=error("Unexpected detail request")
    }
    @Test fun olderQueryAndSameBusinessEpochCannotReplaceCurrentRowsCountsOrFailure()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source);val repo=repository()
        try {
            model.load(101,20);runCurrent();source.pending[0].complete(repo.tasks(101));runCurrent()
            model.applyFilter(TaskQueryFilter(due=TaskDueFilter.TODAY),model.querySelection);runCurrent();assertTrue(model.state.loading);assertTrue(model.state.items.isEmpty());assertFalse(model.state.showsEmpty)
            model.applyFilter(TaskQueryFilter(due=TaskDueFilter.OVERDUE),model.querySelection);runCurrent();val overdue=repo.tasks(101,TaskQueryFilter(due=TaskDueFilter.OVERDUE));source.pending[2].complete(overdue);runCurrent()
            source.pending[1].complete(repo.tasks(101,TaskQueryFilter(due=TaskDueFilter.TODAY)));runCurrent();assertEquals(overdue.items,model.state.items);assertEquals(66,model.state.total)
            model.refreshFilter(model.querySelection);runCurrent();model.load(101,21);runCurrent();source.pending[3].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent()
            assertTrue(model.state.loading);assertNull(model.state.problem);assertEquals(21,model.state.scopeEpoch);source.pending[4].complete(repo.tasks(101));runCurrent()
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun partialZeroDeniedUnavailableAndConfirmedEmptyRemainDifferentRecoverableStates()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source);val repo=repository()
        try {
            model.load(101,30);runCurrent();source.pending[0].complete(repo.tasks(101));runCurrent()
            model.applyFilter(TaskQueryFilter(due=TaskDueFilter.OVERDUE),model.querySelection);runCurrent();source.pending[1].complete(TaskPage(101,emptyList(),9));runCurrent()
            assertTrue(model.state.partial);assertFalse(model.state.showsEmpty)
            listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).forEachIndexed {n,problem->model.refreshFilter(model.querySelection);runCurrent();source.pending[2+n].completeExceptionally(ReadException(problem));runCurrent();assertEquals(problem,model.state.problem);assertFalse(model.state.showsEmpty);assertEquals(TaskDueFilter.OVERDUE,model.state.appliedFilter.due)}
            model.refreshFilter(model.querySelection);runCurrent();source.pending[4].complete(TaskPage(101,emptyList(),0));runCurrent();assertTrue(model.state.showsEmpty);assertNull(model.state.problem);assertFalse(model.state.partial)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun newBusinessResetsFiltersAndOldFilterRefreshCallbacksCannotIssueRequests()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source);val repo=repository()
        try {
            model.load(101,40);runCurrent();source.pending[0].complete(repo.tasks(101));runCurrent();val old=model.querySelection!!
            model.applyFilter(TaskQueryFilter(due=TaskDueFilter.TODAY),old);runCurrent();model.load(202,41);runCurrent();source.pending[2].complete(repo.tasks(202));runCurrent();source.pending[1].complete(repo.tasks(101,TaskQueryFilter(due=TaskDueFilter.TODAY)));runCurrent()
            assertEquals(202,model.state.business);assertEquals(71,model.state.total);assertEquals(TaskQueryFilter(),model.state.appliedFilter)
            val count=source.pending.size;model.applyFilter(TaskQueryFilter("done"),old);model.refreshFilter(old);runCurrent();assertEquals(count,source.pending.size)
            val current=model.querySelection!!;model.refreshFilter(current);runCurrent();model.reconcileCommentOwner(101,42)
            model.applyFilter(TaskQueryFilter(),current);model.refreshFilter(current);source.pending[3].complete(repo.tasks(202));runCurrent()
            assertNull(model.state.business);assertNull(model.querySelection);assertTrue(model.state.items.isEmpty());assertEquals(4,source.pending.size)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun statusMismatchIsAnErrorRatherThanLocalFilteringAwayBadSourceRows()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source);val repo=repository()
        try {
            model.load(101,50);runCurrent();source.pending[0].complete(repo.tasks(101));runCurrent();model.applyFilter(TaskQueryFilter("done"),model.querySelection);runCurrent()
            source.pending[1].complete(repo.tasks(101,TaskQueryFilter("open",TaskDueFilter.TODAY)));runCurrent()
            assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.problem);assertFalse(model.state.showsEmpty);assertTrue(model.state.items.isEmpty())
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
