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
class TaskCommentTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(business: Int=101,id: Int=1101)=JsonContracts.taskDetails(fixture("task-$business-$id"))
    private val context=TaskCommentContext(101,1101,1)
    private val read=TaskCommentRead(context,1)
    private fun provider()=object: TaskCommentDraftSource {
        override suspend fun matchesFixture(detail: TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,this@TaskCommentTest.detail(detail.business,detail.task.id))
    }
    @Test fun validationUsesExecutedWebTrimThenPythonStripAndNeverReadHistoryCap() {
        val s=TaskCommentSession();s.begin(read);s.receive(true,read);s.open(read);val selection=s.state.selection!!
        val cases=JSONObject(fixture("task-comment-validation")).getJSONArray("cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val raw=row.getString("raw");s.update(raw,selection)
            assertEquals(row.getString("preview"),TaskCommentText.preview(raw));assertEquals(row.getBoolean("valid"),s.prepare(selection));assertEquals(raw,s.state.text)
            if(row.getBoolean("valid")) {assertEquals(row.getString("preview"),s.state.review!!.text);s.back(selection)}
        }
        val d=detail();assertTrue(FixtureTaskCommentDraftSource.verified(d,d));assertFalse(FixtureTaskCommentDraftSource.verified(d.copy(description=null),d))
        assertFalse(FixtureTaskCommentDraftSource.verified(d.copy(task=d.task.copy(title=null)),d))
    }
    @Test fun manualReviewBackReopenExplicitClearAndOldUiCallbacksDoNotTouchOtherInput() {
        val s=TaskCommentSession();assertFalse(s.open(read));s.begin(read);assertFalse(s.open(read));s.receive(true,read);assertEquals("",s.state.text);s.open(read);val first=s.state.selection!!
        s.update("  Manual\nsecond line  ",first);assertTrue(s.prepare(first));val preview=s.state.review
        s.update("late",first);assertEquals(preview,s.state.review);assertEquals("  Manual\nsecond line  ",s.state.text)
        s.back(first);s.back(first);assertNull(s.state.selection);s.open(read);val fresh=s.state.selection!!;s.discard(first);s.update("stale",first)
        assertEquals(fresh,s.state.selection);assertEquals("  Manual\nsecond line  ",s.state.text)
        s.discard(fresh);assertTrue(s.state.text.isEmpty());assertNull(s.state.selection);s.pause();s.begin(read);s.receive(true,read);assertTrue(s.state.text.isEmpty())
    }
    @Test fun privateTaskBuffersHideOnReadOrBackAndAreClearedAcrossBusinessEpoch() {
        val s=TaskCommentSession();s.begin(read);s.receive(true,read);s.open(read);s.update("Task A",s.state.selection!!);s.pause();assertTrue(s.state.text.isEmpty());assertNull(s.state.read)
        val fresh=read.copy(revision=2);s.begin(fresh);s.receive(true,read);assertFalse(s.state.available);s.receive(true,fresh);assertEquals("Task A",s.state.text)
        val other=TaskCommentRead(context.copy(task=1103),3);s.begin(other);s.receive(true,other);assertTrue(s.state.text.isEmpty());s.open(other);s.update("Task B",s.state.selection!!)
        s.begin(fresh);s.receive(true,fresh);assertEquals("Task A",s.state.text)
        s.begin(fresh);s.receive(false,fresh);assertFalse(s.state.available);assertTrue(s.state.text.isEmpty());s.begin(fresh);s.receive(true,fresh);assertEquals("Task A",s.state.text)
        s.retainOwner(101,1);assertTrue(s.state.text.isEmpty());s.begin(fresh);s.receive(true,fresh);assertEquals("Task A",s.state.text)
        s.retainOwner(101,2);val epoch=TaskCommentRead(context.copy(epoch=2),4);s.begin(epoch);s.receive(true,epoch);assertTrue(s.state.text.isEmpty())
        s.open(epoch);s.update("Epoch input",s.state.selection!!);val business=TaskCommentRead(context.copy(business=202,epoch=2),5);s.begin(business);s.receive(true,business);assertTrue(s.state.text.isEmpty())
        s.begin(read.copy(revision=0));assertNull(s.state.read);assertFalse(s.state.available)
    }
    private fun repository(requests: MutableList<ReadRequest> = mutableListOf())=APIReadRepository(ReadTransport {r->
        requests+=r;val business=r.query.getValue("business");val id=r.path.trimEnd('/').substringAfterLast('/')
        ReadResponse(200,fixture(if(id=="tasks")"tasks-$business" else "task-$business-$id"))
    })
    @Test fun actualTaskDetailCommentReviewDoesNotCreateCommentRequestRowsStatusOrReadEffects()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=repository(requests);val model=TaskListViewModel(repo,provider());val opaque=TaskListViewModel(repo)
        try {
            model.load(101,10);runCurrent();model.search("Alpha");model.filter("open");model.open(1101);runCurrent()
            val rows=model.state.items;val d=model.state.detail;val count=requests.size;val comment=model.comment!!;val r=comment.state.read!!;comment.open(r);val selection=comment.state.selection!!
            comment.update("  Manual task comment  ",selection);comment.prepare(selection)
            assertEquals("Manual task comment",comment.state.review!!.text);assertEquals(TaskCommentPhase.REVIEW,comment.state.phase)
            assertEquals(count,requests.size);assertEquals(rows,model.state.items);assertEquals(d,model.state.detail)
            model.back();assertTrue(comment.state.text.isEmpty());assertEquals("Alpha",model.state.query);assertEquals("open",model.state.status)
            model.open(1101);runCurrent();assertEquals("  Manual task comment  ",comment.state.text)
            model.open(1103);runCurrent();assertTrue(comment.state.text.isEmpty());model.open(1101);runCurrent();assertTrue(comment.state.text.contains("Manual"))
            opaque.load(101,10);runCurrent();opaque.open(1101);runCurrent();assertNull(opaque.comment)
            model.load(101);runCurrent();model.open(1101);runCurrent();assertFalse(comment.state.available);assertNull(comment.state.read)
        } finally {model.viewModelScope.cancel();opaque.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class Controlled: TaskReadRepository {
        val details=mutableListOf<CompletableDeferred<TaskDetails>>();var page: TaskPage?=null
        override suspend fun tasks(business: Int)=page!!
        override suspend fun taskDetails(business: Int,id: Int)=CompletableDeferred<TaskDetails>().also {details+=it}.await()
    }
    @Test fun deniedUnavailableAndUnverifiedDetailHideCommentWhileVerifiedRetryRestoresIt()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();repo.page=JsonContracts.tasks(fixture("tasks-101"));val model=TaskListViewModel(repo,provider())
        try {
            model.load(101,1);runCurrent();model.open(1101);runCurrent();repo.details[0].complete(detail());runCurrent()
            val comment=model.comment!!;comment.open(comment.state.read!!);comment.update("Keep after error",comment.state.selection!!)
            listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).forEachIndexed {n,error->
                model.open(1101);assertFalse(comment.state.available);assertTrue(comment.state.text.isEmpty());runCurrent();repo.details[1+n*2].completeExceptionally(ReadException(error));runCurrent()
                assertEquals(error,model.state.detailProblem);assertNull(model.state.detail)
                model.open(1101);runCurrent();repo.details[2+n*2].complete(detail());runCurrent();assertEquals("Keep after error",comment.state.text)
            }
            model.open(1101);runCurrent();repo.details[5].complete(detail().copy(description=null));runCurrent();assertFalse(comment.state.available);assertTrue(comment.state.text.isEmpty())
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun delayedFixtureSourceCannotRepopulateOldTaskEpochBusinessOrClosedRoute()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val pending=mutableListOf<CompletableDeferred<Boolean>>()
        val source=object: TaskCommentDraftSource {override suspend fun matchesFixture(detail: TaskDetails)=CompletableDeferred<Boolean>().also {pending+=it}.await()};val model=TaskListViewModel(repository(),source)
        try {
            model.load(101,30);runCurrent();model.open(1101);runCurrent();model.open(1103);runCurrent();pending[1].complete(true);runCurrent();pending[0].complete(true);runCurrent()
            assertEquals(1103,model.state.detail!!.task.id);assertEquals(1103,model.comment!!.state.read!!.context.task)
            model.open(1101);runCurrent();model.load(101,31);runCurrent();model.open(1101);runCurrent();pending[2].complete(true);runCurrent();assertNull(model.state.detail);assertTrue(model.state.detailLoading)
            pending[3].complete(true);runCurrent();model.open(1101);runCurrent();model.back();pending[4].complete(true);runCurrent();assertNull(model.state.detail);assertNull(model.comment!!.state.read)
            model.open(1101);runCurrent();model.load(202,32);runCurrent();model.open(1201);runCurrent();pending[6].complete(true);runCurrent();pending[5].complete(true);runCurrent()
            assertEquals(1201,model.state.detail!!.task.id);assertEquals(202,model.comment!!.state.read!!.context.business)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun oldIndependentDetailCannotOverrideCurrentReadOrRestoreCommentVisibility()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();repo.page=JsonContracts.tasks(fixture("tasks-101"));val model=TaskListViewModel(repo,provider())
        try {
            model.load(101,40);runCurrent();model.open(1101);runCurrent();model.open(1103);runCurrent()
            repo.details[1].complete(detail(101,1103));runCurrent();repo.details[0].complete(detail());runCurrent()
            assertEquals(1103,model.state.detail!!.task.id);assertEquals(1103,model.comment!!.state.read!!.context.task)
            model.open(1101);runCurrent();model.back();repo.details[2].complete(detail());runCurrent();assertNull(model.state.detail);assertFalse(model.comment!!.state.available)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun offTabOwnerReconciliationRevokesDraftTargetAndPendingVerificationWithoutRequests()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val model=TaskListViewModel(repository(requests),provider())
        val pending=CompletableDeferred<Boolean>();val held=TaskListViewModel(repository(),object: TaskCommentDraftSource {override suspend fun matchesFixture(detail: TaskDetails)=pending.await()})
        try {
            model.load(101,40);runCurrent();model.open(1101);runCurrent();val comment=model.comment!!;comment.open(comment.state.read!!);comment.update("Private old Business",comment.state.selection!!)
            val count=requests.size;model.reconcileCommentOwner(202,41);assertNull(comment.state.read);assertTrue(comment.state.text.isEmpty());assertNull(model.state.detail);assertNull(model.state.selectedID);assertEquals(count,requests.size)
            model.load(101,42);runCurrent();model.open(1101);runCurrent();assertTrue(comment.state.text.isEmpty())
            held.load(101,50);runCurrent();held.open(1101);runCurrent();held.reconcileCommentOwner(202,51);pending.complete(true);runCurrent()
            assertNull(held.state.detail);assertFalse(held.comment!!.state.available)
        } finally {model.viewModelScope.cancel();held.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
