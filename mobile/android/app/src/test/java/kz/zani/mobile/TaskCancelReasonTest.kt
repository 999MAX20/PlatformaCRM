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
class TaskCancelReasonTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val read=TaskCommentRead(TaskCommentContext(101,1101,1),1)
    private fun provider()=object: TaskCommentDraftSource {
        override suspend fun matchesFixture(detail: TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,JsonContracts.taskDetails(fixture("task-${detail.business}-${detail.task.id}")))
    }
    private fun repository(requests: MutableList<ReadRequest> = mutableListOf())=APIReadRepository(ReadTransport {r->
        requests+=r;val business=r.query.getValue("business").toInt();val id=if(r.path.endsWith("tasks/"))null else r.path.trimEnd('/').substringAfterLast('/').toInt()
        FixtureTaskQueries.response(fixture("task-query-source-$business"),business,r.query,id)
    })
    @Test fun sourceWebAndSerializerRulesPreserveRawInputAndUseCodepointsNotUtf16ForMaximum() {
        val s=TaskCancelReasonSession();s.begin(read);s.receive(true,"open",read);s.open(read);val selection=s.state.selection!!
        val reference=JSONObject(fixture("task-cancel-reason-validation"));val cases=reference.getJSONArray("cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val raw=row.getString("raw");val expected=if(row.isNull("problem"))null else TaskCancelReasonProblem.valueOf(row.getString("problem").uppercase())
            s.update(raw,selection);assertEquals(row.getString("preview"),TaskCancelReasonText.preview(raw));assertEquals(expected,TaskCancelReasonText.problem(raw));assertEquals(expected==null,s.prepare(selection));assertEquals(raw,s.state.text)
            if(expected==null) {assertEquals(row.getString("preview"),s.state.review!!.text);s.back(selection)}
        }
        val malformed=reference.getJSONArray("kotlin_only_invalid_utf16")
        for(n in 0 until malformed.length()) {
            val units=malformed.getJSONObject(n).getJSONArray("units");val raw=String(CharArray(units.length()){units.getInt(it).toChar()})
            assertEquals(TaskCancelReasonProblem.CHARACTERS,TaskCancelReasonText.problem(raw))
        }
    }
    @Test fun reviewBackReopenClearAndDistinctCommentEngineKeepOnlyOwnManualText() {
        val s=TaskCancelReasonSession();assertFalse(s.open(read));s.begin(read);s.receive(true,"open",read);s.open(read);val first=s.state.selection!!
        s.update("  Manual reason\nsecond line  ",first);assertTrue(s.prepare(first));val review=s.state.review;s.update("late edit",first);assertEquals(review,s.state.review)
        s.back(first);s.back(first);assertNull(s.state.selection);assertTrue(s.state.text.startsWith("  Manual"));s.open(read);val fresh=s.state.selection!!
        s.discard(first);s.update("stale",first);assertEquals(fresh,s.state.selection);assertTrue(s.state.text.startsWith("  Manual"))
        val comment=TaskCommentSession();comment.begin(read);comment.receive(true,read);comment.open(read);comment.update("Independent comment input",comment.state.selection!!)
        assertNotEquals(comment.state.text,s.state.text);s.discard(fresh);assertTrue(s.state.text.isEmpty());assertNull(s.state.selection)
    }
    @Test fun sourceStatusReadGenerationAndBusinessEpochGateAvailabilityWithoutNewPermissions() {
        val s=TaskCancelReasonSession();s.begin(read);s.receive(true,"open",read);s.open(read);s.update("Own Task A reason",s.state.selection!!);s.pause();assertTrue(s.state.text.isEmpty())
        val fresh=read.copy(revision=2)
        listOf("done","cancelled","future_status","",null).forEach {status->s.begin(fresh);s.receive(true,status,fresh);assertFalse(s.state.available);assertTrue(s.state.text.isEmpty());assertFalse(s.open(fresh))}
        s.begin(fresh);s.receive(false,"open",fresh);assertFalse(s.state.available)
        s.begin(fresh);s.receive(true,"open",read);assertFalse(s.state.available);s.receive(true,"in_progress",fresh);assertEquals("Own Task A reason",s.state.text)
        val other=TaskCommentRead(read.context.copy(task=1102),3);s.begin(other);s.receive(true,"open",other);assertTrue(s.state.text.isEmpty())
        s.begin(fresh);s.receive(true,"open",fresh);assertEquals("Own Task A reason",s.state.text)
        s.retainOwner(202,2);s.begin(fresh);s.receive(true,"open",fresh);assertTrue(s.state.text.isEmpty())
    }
    @Test fun actualTaskOwnerHasOneLocalEditorAndNoStatusCommentRequestOrRowEffects()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=repository(requests);val model=TaskListViewModel(repo,provider());val opaque=TaskListViewModel(repo)
        try {
            model.load(101,10);runCurrent();model.applyFilter(TaskQueryFilter("open",TaskDueFilter.TODAY),model.querySelection);runCurrent();model.open(1101);runCurrent()
            val original=model.state.detail;val rows=model.state.items;val reason=model.cancelReason!!;val comment=model.comment!!;val r=reason.state.read!!
            model.openComment(r);comment.update("Own comment",comment.state.selection!!);model.openCancelReason(r);assertNull(comment.state.selection);assertEquals("Own comment",comment.state.text);assertTrue(reason.state.text.isEmpty())
            val first=reason.state.selection!!;reason.update("AB",first);reason.prepare(first);assertEquals(TaskCancelReasonProblem.MINIMUM,reason.state.problem);assertEquals("AB",reason.state.text)
            val count=requests.size;reason.update("  Manual reason  ",first);reason.prepare(first);assertEquals("Manual reason",reason.state.review!!.text);assertEquals(count,requests.size);assertEquals(original,model.state.detail);assertEquals(rows,model.state.items)
            model.openComment(r);assertNull(reason.state.selection);assertEquals("  Manual reason  ",reason.state.text);assertEquals("Own comment",comment.state.text)
            model.openCancelReason(r);val current=reason.state.selection!!;reason.discard(first);assertEquals(current,reason.state.selection)
            model.back();assertTrue(reason.state.text.isEmpty());model.open(1101);runCurrent();assertEquals("  Manual reason  ",reason.state.text)
            opaque.load(101,11);runCurrent();assertNull(opaque.cancelReason)
        } finally {model.viewModelScope.cancel();opaque.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun closedSelectionAndOldControlsCannotEnableReasonOrAlterCurrentTask()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val model=TaskListViewModel(repository(requests),provider())
        try {
            model.load(101,20);runCurrent();model.applyFilter(TaskQueryFilter("open",TaskDueFilter.TODAY),model.querySelection);runCurrent();model.open(1101);runCurrent();val oldRead=model.cancelReason!!.state.read!!;val oldTarget=model.detailSelection!!
            model.applyFilter(TaskQueryFilter("done"),model.querySelection);runCurrent();model.open(1103);runCurrent()
            assertFalse(model.cancelReason!!.state.available);assertTrue(model.comment!!.state.available);val count=requests.size
            model.openCancelReason(oldRead);model.back(oldTarget);model.retryDetail(oldTarget);runCurrent();assertEquals(count,requests.size);assertEquals(1103,model.state.selectedID);assertNull(model.cancelReason!!.state.selection)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class Controlled: TaskReadRepository {
        val details=mutableListOf<CompletableDeferred<TaskDetails>>();var page: TaskPage?=null
        override suspend fun tasks(business: Int)=page!!
        override suspend fun taskDetails(business: Int,id: Int)=CompletableDeferred<TaskDetails>().also {details+=it}.await()
    }
    @Test fun readFailureRecoveryAndOffTabRevocationPreserveOwnTextButHideUntrustedState()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();repo.page=JsonContracts.tasks(fixture("tasks-101"));val model=TaskListViewModel(repo,provider())
        try {
            model.load(101,30);runCurrent();model.open(1101);runCurrent();val detail=JsonContracts.taskDetails(fixture("task-101-1101"));repo.details[0].complete(detail);runCurrent();val reason=model.cancelReason!!;model.openCancelReason(reason.state.read!!);reason.update("Keep after error",reason.state.selection!!)
            listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).forEachIndexed {n,error->model.open(1101);assertFalse(reason.state.available);assertTrue(reason.state.text.isEmpty());runCurrent();repo.details[1+n*2].completeExceptionally(ReadException(error));runCurrent();assertEquals(error,model.state.detailProblem);model.open(1101);runCurrent();repo.details[2+n*2].complete(detail);runCurrent();assertEquals("Keep after error",reason.state.text)}
            model.open(1101);runCurrent();model.reconcileCommentOwner(202,31);repo.details[5].complete(detail);runCurrent();assertNull(reason.state.read);assertTrue(reason.state.text.isEmpty());assertNull(model.state.business)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
