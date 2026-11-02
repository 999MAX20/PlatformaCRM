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
class TaskUndoCancelTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=3167)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun source(payload:TaskDetails=detail(),epoch:Int=200,revision:Int=1)=TaskUndoCancelSource(TaskCommentRead(TaskCommentContext(payload.business,payload.task.id,epoch),revision),payload.task)
    private fun port()=FixtureTaskUndoCancelPort(fixture("task-undo-cancel-outcome"))
    private val context=TaskCommentContext(101,3167,200)
    private class Controlled(override val grants:List<SyntheticTaskUndoCancelGrant>):SyntheticTaskUndoCancelPort {val attempts=mutableListOf<TaskUndoCancelAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskUndoCancelOutcome>>()
        override suspend fun execute(attempt:TaskUndoCancelAttempt):SyntheticTaskUndoCancelOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskUndoCancelOutcome>().also {pending+=it}.await()}
    }
    @Test fun cancelledOnlyAndIndependentUpdateDoNotRequireAuditProjectionOrMemberFlag()=runTest {
        assertNull(SyntheticTaskUndoCancelGrant(101,3167,9001,false).authorization(context));assertNull(SyntheticTaskUndoCancelGrant(202,3167,9001,true).authorization(context));assertNull(SyntheticTaskUndoCancelGrant(101,3167,0,true).authorization(context))
        for(status in listOf("open","in_progress","done","waiting","")) {val s=source().copy(task=detail().task.copy(status=status));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(TaskUndoCancelLedger().begin(TaskUndoCancelReview(s,1),port().grants[0].authorization(context)!!))}
    }
    @Test fun shared39CasesVerifyReturnedStatusAndPreserveCompletionInsteadOfReopenClearing()=runTest {
        val cases=JSONObject(fixture("task-undo-cancel-outcome")).getJSONArray("validation_cases");assertEquals(39,cases.length())
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val l=TaskUndoCancelLedger();val a=port().grants[0].authorization(context)!!;val review=TaskUndoCancelReview(source(),1);val attempt=l.begin(review,a)!!;assertNull(l.begin(review,a));val wire=row.getJSONObject("response")
            l.complete(attempt,SyntheticTaskUndoCancelOutcome.Response(row.getInt("status"),wire.toString()));val record=l.visible(a)!!;assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskUndoCancelPhase.CONFIRMED else TaskUndoCancelPhase.UNKNOWN,record.phase);l.complete(attempt,SyntheticTaskUndoCancelOutcome.RejectedWithoutWrite);assertEquals(record,l.visible(a));assertEquals(review,record.attempt.review);if(record.phase==TaskUndoCancelPhase.UNKNOWN)assertFalse(l.acknowledge(a))
            record.result?.let {assertEquals(wire.getString("status"),it.status);assertEquals(if(wire.isNull("completed_at"))null else wire.getString("completed_at"),it.completedAt);assertEquals(if(wire.isNull("completed_by"))null else wire.getInt("completed_by"),it.completedBy)}
        }
    }
    @Test fun stringFixtureFlagsCannotBecomeUpdateAuthority()=runTest {
        for(key in listOf("update","actor")) {val raw=JSONObject(fixture("task-undo-cancel-outcome"));raw.getJSONArray("scenarios").getJSONObject(0).getJSONObject("grant").put(key,if(key=="actor")"9001" else "true");assertTrue(FixtureTaskUndoCancelPort(raw.toString()).grants.isEmpty())}
        val raw=JSONObject(fixture("task-undo-cancel-outcome")).put("fixture_only","true");assertTrue(FixtureTaskUndoCancelPort(raw.toString()).grants.isEmpty())
    }
    @Test fun reviewHasNoPredictedTargetAndStalePendingControlsNeverDuplicate()=runTest {
        val p=Controlled(port().grants);val m=TaskUndoCancelModel(p,backgroundScope);m.bind(source());m.prepare(m.control);assertEquals("cancelled",m.review!!.source.task.status);assertNull(m.submission);val stale=m.control;m.back(stale);m.prepare(m.control);m.submit(stale);assertTrue(p.attempts.isEmpty());val submit=m.control;val job=async {m.submit(submit)};runCurrent();val pending=m.control;val record=m.submission!!;m.submit(pending);m.back(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission);assertEquals("cancelled",m.source!!.task.status);p.pending[0].complete(SyntheticTaskUndoCancelOutcome.Unknown);job.await()
    }
    @Test fun matchingAnyRestoredStatusAndNewEpochCannotProveKeylessUnknown()=runTest {
        val p=Controlled(port().grants);val m=TaskUndoCancelModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();p.pending[0].completeExceptionally(CancellationException("synthetic"));job.await();val attempt=m.submission!!.attempt
        for(status in listOf("open","in_progress","done")) {m.bind(source(revision=2).copy(task=detail().task.copy(status=status)));assertTrue(m.blocked);assertTrue(m.canPresent);assertFalse(m.canPrepare);assertEquals(attempt,m.submission!!.attempt)}
        m.bind(source(epoch=201,revision=3));assertNull(m.submission);assertTrue(m.blocks(context));m.bind(null);assertEquals(1,m.retainedAttemptCount);assertTrue(m.blocks(context))
    }
    @Test fun lateForeignOutcomeDoesNotMutateReplacementAndConfirmedReadIsConsumed()=runTest {
        val fixture=port();val p=Controlled(fixture.grants);val m=TaskUndoCancelModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();val foreign=detail(202,1201);m.bind(source(foreign.copy(task=foreign.task.copy(status="cancelled")),202));val replacement=m.control;p.pending[0].complete(fixture.execute(p.attempts[0]));job.await();assertEquals(replacement,m.control);assertNull(m.submission);assertTrue(m.canPrepare)
        m.bind(source());val record=m.submission!!;assertEquals(TaskUndoCancelPhase.CONFIRMED,record.phase);assertEquals("open",record.result!!.status);assertEquals("cancelled",m.source!!.task.status);m.acknowledge(m.control,record);m.prepare(m.control);assertTrue(m.consumed);assertNull(m.review);m.bind(source(revision=2));assertTrue(m.canPrepare)
    }
    @Test fun noWriteRequiresNewExplicitReviewWithoutBlindReplay()=runTest {
        val original=detail(101,1401);val m=TaskUndoCancelModel(port(),backgroundScope);m.bind(source(original.copy(task=original.task.copy(status="cancelled"))));m.prepare(m.control);m.submit(m.control);val record=m.submission!!;assertEquals(TaskUndoCancelPhase.REJECTED,record.phase);m.acknowledge(m.control,record);assertTrue(m.canPrepare);assertNull(m.review)
    }
    private inner class Repo:TaskReadRepository {var selected=detail()
        override suspend fun tasks(business:Int):TaskPage {if(selected.business==business && selected.task.id==3167) {val response=FixtureTaskQueries.response(fixture("task-query-source-$business"),business,mapOf("business" to business.toString(),"limit" to "50","status" to "cancelled"));return JsonContracts.tasks(response.body)};return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails=if(selected.business==business && selected.task.id==id)selected else detail(business,id)
    }
    private fun origin(allowed:List<TaskDetails>)=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail in allowed}
    @Test fun defaultAndGetOnlyCompositionDoNotGrantUndo()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val plain=TaskListViewModel(repo);val m=TaskListViewModel(repo,undoCancelSubmission=port())
        try {m.load(101,203);runCurrent();m.open(3167);runCurrent();assertNull(plain.undoCancelAction);assertNull(m.undoCancelAction!!.source)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun existingCancelledQueryReachesFixtureWithoutOptimisticTaskOrExtraRead()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {r->requests+=r;val b=r.query.getValue("business").toInt();val id=if(r.path.endsWith("tasks/"))null else r.path.trimEnd('/').substringAfterLast('/').toInt();FixtureTaskQueries.response(fixture("task-query-source-$b"),b,r.query,id)})
        val reopen=object:SyntheticTaskReopenPort {override val grants=listOf(SyntheticTaskReopenGrant(101,3167,9001,true));override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}
        val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),reopenSubmission=reopen,fileMetadataPort=FixtureTaskFileMetadataPort(fixture("task-file-metadata")),undoCancelSubmission=port())
        try {m.load(101,204);runCurrent();m.applyFilter(TaskQueryFilter("cancelled"),m.querySelection);runCurrent();assertEquals(listOf(3167),m.state.items.map {it.id});assertEquals(1,m.state.total);m.open(3167);runCurrent();val u=m.undoCancelAction!!;val before=m.state.detail;val items=m.state.items;val reads=requests.size;m.prepareUndoCancel(u.control,m.control);assertEquals("cancelled",u.review!!.source.task.status);u.submit(u.control);val record=u.submission!!;assertEquals(TaskUndoCancelPhase.CONFIRMED,record.phase);assertEquals(before,m.state.detail);assertEquals(items,m.state.items);assertEquals(reads,requests.size)
            m.fileMetadata!!.load(m.fileMetadata!!.control);assertEquals(record,u.submission);assertEquals(before,m.state.detail);u.acknowledge(u.control,record);m.prepareReopen(m.reopenAction!!.control,m.control);assertNull(m.reopenAction!!.review);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun keylessUndoUnknownBlocksFivePeersAfterMatchingRestoredReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val initial=detail();val open=initial.copy(task=initial.task.copy(status="open"));val done=initial.copy(task=initial.task.copy(status="done"));val repo=Repo();val p=Controlled(port().grants)
        val c=object:SyntheticTaskCompletePort {override val grants=listOf(SyntheticTaskCompleteGrant(101,3167,9001,true));override suspend fun execute(attempt:TaskCompletionAttempt)=SyntheticTaskCompleteOutcome.Unknown}
        val a=object:SyntheticTaskSelfAssignPort {override val grants=listOf(SyntheticTaskSelfAssignGrant(101,3167,9001,true,true));override suspend fun execute(attempt:TaskSelfAssignmentAttempt)=SyntheticTaskSelfAssignOutcome.Unknown}
        val s=object:SyntheticTaskStartPort {override val grants=listOf(SyntheticTaskStartGrant(101,3167,9001,true));override suspend fun execute(attempt:TaskStartAttempt)=SyntheticTaskStartOutcome.Unknown}
        val r=object:SyntheticTaskReopenPort {override val grants=listOf(SyntheticTaskReopenGrant(101,3167,9001,true));override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}
        val w=object:SyntheticTaskWatcherPort {override val grants=listOf(SyntheticTaskWatcherGrant(101,3167,9001,true,true));override suspend fun execute(attempt:TaskWatcherAttempt)=SyntheticTaskWatcherOutcome.Unknown}
        val m=TaskListViewModel(repo,commentSource=origin(listOf(initial,open,done)),completeSubmission=c,selfAssignSubmission=a,startSubmission=s,reopenSubmission=r,watcherSubmission=w,undoCancelSubmission=p)
        try {m.load(101,205);runCurrent();m.open(3167);runCurrent();val u=m.undoCancelAction!!;m.prepareUndoCancel(u.control,m.control);val job=async {u.submit(u.control)};runCurrent();p.pending[0].complete(SyntheticTaskUndoCancelOutcome.Unknown);job.await();repo.selected=open;m.retryDetail(m.detailSelection);runCurrent();m.prepareCompletion(m.completion!!.control,m.control);m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);m.prepareStart(m.startAction!!.control,m.control);m.prepareWatcher(m.watcherAction!!.control,m.control);assertTrue(m.completion!!.canPrepare);assertTrue(m.selfAssignment!!.canPrepare);assertTrue(m.startAction!!.canPrepare);assertTrue(m.watcherAction!!.canPrepare);assertNull(m.completion!!.review);assertNull(m.selfAssignment!!.review);assertNull(m.startAction!!.review);assertNull(m.watcherAction!!.review)
            repo.selected=done;m.retryDetail(m.detailSelection);runCurrent();m.prepareReopen(m.reopenAction!!.control,m.control);assertTrue(m.reopenAction!!.canPrepare);assertNull(m.reopenAction!!.review);assertEquals(TaskUndoCancelPhase.UNKNOWN,u.submission!!.phase);m.load(202,206);runCurrent();m.open(1201);runCurrent();assertFalse(m.taskActionOccupied);assertEquals(1,u.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun allFiveEarlierUnknownActionsBlockNewlyEligibleUndoCancel()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {for(kind in 0..4) {val initial=detail(101,if(kind==3)1103 else 1101);val cancelled=initial.copy(task=initial.task.copy(status="cancelled"));val repo=Repo().also {it.selected=initial}
            val c=object:SyntheticTaskCompletePort {override val grants=FixtureTaskCompletePort(fixture("task-complete-outcome")).grants;override suspend fun execute(attempt:TaskCompletionAttempt)=SyntheticTaskCompleteOutcome.Unknown}
            val a=object:SyntheticTaskSelfAssignPort {override val grants=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")).grants;override suspend fun execute(attempt:TaskSelfAssignmentAttempt)=SyntheticTaskSelfAssignOutcome.Unknown}
            val s=object:SyntheticTaskStartPort {override val grants=FixtureTaskStartPort(fixture("task-start-outcome")).grants;override suspend fun execute(attempt:TaskStartAttempt)=SyntheticTaskStartOutcome.Unknown}
            val r=object:SyntheticTaskReopenPort {override val grants=FixtureTaskReopenPort(fixture("task-reopen-outcome")).grants;override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}
            val w=object:SyntheticTaskWatcherPort {override val grants=FixtureTaskWatcherPort(fixture("task-watcher-outcome")).grants;override suspend fun execute(attempt:TaskWatcherAttempt)=SyntheticTaskWatcherOutcome.Unknown}
            val u=Controlled(listOf(SyntheticTaskUndoCancelGrant(101,initial.task.id,9001,true)));val m=TaskListViewModel(repo,commentSource=origin(listOf(initial,cancelled)),completeSubmission=c,selfAssignSubmission=a,startSubmission=s,reopenSubmission=r,watcherSubmission=w,undoCancelSubmission=u)
            try {m.load(101,207);runCurrent();m.open(initial.task.id);runCurrent();when(kind) {0->{m.prepareCompletion(m.completion!!.control,m.control);m.completion!!.submit(m.completion!!.control)};1->{m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);m.selfAssignment!!.submit(m.selfAssignment!!.control)};2->{m.prepareStart(m.startAction!!.control,m.control);m.startAction!!.submit(m.startAction!!.control)};3->{m.prepareReopen(m.reopenAction!!.control,m.control);m.reopenAction!!.submit(m.reopenAction!!.control)};else->{m.prepareWatcher(m.watcherAction!!.control,m.control);m.watcherAction!!.submit(m.watcherAction!!.control)}}
                repo.selected=cancelled;m.retryDetail(m.detailSelection);runCurrent();m.prepareUndoCancel(m.undoCancelAction!!.control,m.control);assertTrue(m.undoCancelAction!!.canPrepare);assertNull(m.undoCancelAction!!.review);assertTrue(m.taskActionOccupied);assertEquals(0,m.undoCancelAction!!.retainedAttemptCount)
            } finally {m.viewModelScope.cancel()}
        }} finally {Dispatchers.resetMain()}
    }
    @Test fun cancelledRereadCannotTurnCancellationUnknownIntoUndoAuthority()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val original=detail(101,1101);val cancelled=original.copy(task=original.task.copy(status="cancelled"));val repo=Repo().also {it.selected=original};val cancel=object:SyntheticTaskCancelPort {override val grants=FixtureTaskCancelPort.fromJSON(fixture("task-cancel-outcome").toString()).grants;override suspend fun execute(attempt:TaskCancelAttempt)=SyntheticTaskCancelOutcome.Unknown};val u=Controlled(listOf(SyntheticTaskUndoCancelGrant(101,1101,9001,true)));val m=TaskListViewModel(repo,commentSource=origin(listOf(original,cancelled)),cancelSubmission=cancel,undoCancelSubmission=u)
        try {m.load(101,208);runCurrent();m.open(1101);runCurrent();val reason=m.cancelReason!!;m.openCancelReason(reason.state.read!!);reason.update("Manual source reason",reason.inputControl);reason.prepare(reason.control);reason.submit(reason.state.review!!,reason.control);reason.close(expected=reason.returnControl);repo.selected=cancelled;m.retryDetail(m.detailSelection);runCurrent();m.prepareUndoCancel(m.undoCancelAction!!.control,m.control);assertTrue(m.undoCancelAction!!.canPrepare);assertNull(m.undoCancelAction!!.review);assertTrue(reason.submissionBlocked)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
