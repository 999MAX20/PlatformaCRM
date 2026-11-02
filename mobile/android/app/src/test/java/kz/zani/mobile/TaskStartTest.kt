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
class TaskStartTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun source(payload:TaskDetails=detail(),epoch:Int=160,revision:Int=1)=TaskStartSource(TaskCommentRead(TaskCommentContext(payload.business,payload.task.id,epoch),revision),payload.task,payload.assignee)
    private fun port()=FixtureTaskStartPort(fixture("task-start-outcome"))
    private val context=TaskCommentContext(101,1101,160)
    private class Controlled(override val grants:List<SyntheticTaskStartGrant>):SyntheticTaskStartPort {
        val attempts=mutableListOf<TaskStartAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskStartOutcome>>()
        override suspend fun execute(attempt:TaskStartAttempt):SyntheticTaskStartOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskStartOutcome>().also {pending+=it}.await()}
    }
    @Test fun openOnlySeparateUpdateGrantAndUnknownIdentityNeverBecomeAuthority()=runTest {
        assertNull(SyntheticTaskStartGrant(101,1101,9001,false).authorization(context));assertNull(SyntheticTaskStartGrant(202,1101,9001,true).authorization(context));assertNull(SyntheticTaskStartGrant(101,1101,0,true).authorization(context))
        for(status in listOf("in_progress","done","cancelled","waiting","")) {val s=source().copy(task=detail().task.copy(status=status));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(TaskStartLedger().begin(TaskStartReview(s,1),port().grants.firstNotNullOf {it.authorization(context)}))}
        val p=Controlled(emptyList());val model=TaskStartModel(p,backgroundScope);model.bind(source());model.prepare(model.control);model.submit(model.control);assertFalse(model.canPresent);assertTrue(p.attempts.isEmpty())
    }
    @Test fun exactResultCasesPreserveKnownNullKnownPersonAndUnknownAssigneeDistinction() {
        val cases=JSONObject(fixture("task-start-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val o=JSONObject(fixture("task-101-1101"));val fields=o.getJSONObject("details")
            if(row.has("source_assignee"))fields.put("assignee",row.get("source_assignee"));if(row.optBoolean("omit_source_assignee",false))fields.remove("assignee")
            val snapshot=source(JsonContracts.taskDetails(o.toString()));val review=TaskStartReview(snapshot,1);val ledger=TaskStartLedger();val attempt=ledger.begin(review,auth)!!;assertNull(ledger.begin(review,auth))
            ledger.complete(attempt,SyntheticTaskStartOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!;assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskStartPhase.CONFIRMED else TaskStartPhase.UNKNOWN,record.phase)
            ledger.complete(attempt,SyntheticTaskStartOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(review,record.attempt.review);if(record.phase==TaskStartPhase.UNKNOWN)assertFalse(ledger.acknowledge(auth))
        }
        assertNull(TaskStartResult.decode("[]"));assertNull(TaskStartResult.decode("not json"))
    }
    @Test fun identicalPreviewAndForeignBindingConsumeOldSubmitWithoutPortCall()=runTest {
        val p=Controlled(port().grants);val m=TaskStartModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val old=m.control!!;m.back(old);m.prepare(m.control);m.submit(old);assertTrue(p.attempts.isEmpty())
        m.bind(source(detail(202,1201),162));m.submit(old);assertTrue(p.attempts.isEmpty());assertTrue(m.canPrepare)
    }
    @Test fun pendingDuplicateAndMatchingInProgressReadCannotClearUnknownStart()=runTest {
        val p=Controlled(port().grants);val m=TaskStartModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val submit=m.control!!;val job=async {m.submit(submit)};runCurrent();val pending=m.control!!;val record=m.submission!!
        m.submit(submit);m.submit(pending);m.back(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission)
        m.bind(source(detail().copy(task=detail().task.copy(status="in_progress")),revision=2));assertFalse(m.source!!.valid);assertTrue(m.canPresent);assertTrue(m.blocked);p.pending[0].complete(SyntheticTaskStartOutcome.Unknown);job.await()
        assertEquals(TaskStartPhase.UNKNOWN,m.submission!!.phase);m.bind(source(detail().copy(task=detail().task.copy(status="done")),epoch=161,revision=3));assertNull(m.submission);assertTrue(m.blocks(context));assertTrue(m.canPresent);assertFalse(m.canPrepare)
    }
    @Test fun lateResultDoesNotRevokeNewOwnerAndDoesNotAssignActor()=runTest {
        val fixture=port();val p=Controlled(fixture.grants);val m=TaskStartModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();m.bind(source(detail(202,1201),162));val current=m.control
        p.pending[0].complete(fixture.execute(p.attempts[0]));job.await();assertEquals(current,m.control);assertNull(m.submission);assertTrue(m.canPrepare);m.bind(source());val result=m.submission!!;assertEquals(TaskStartPhase.CONFIRMED,result.phase);assertNull(result.result!!.assignee)
    }
    @Test fun confirmedReadConsumptionAndNoWriteRetryBothRequireExplicitNewReview()=runTest {
        val m=TaskStartModel(port(),backgroundScope);m.bind(source());m.prepare(m.control);m.submit(m.control);val result=m.submission!!;m.acknowledge(m.control,result);m.prepare(m.control);assertTrue(m.consumed);assertNull(m.review);assertEquals("open",m.source!!.task.status)
        m.bind(source(revision=2));assertTrue(m.canPrepare);m.bind(source(detail(101,1401)));m.prepare(m.control);m.submit(m.control);val noWrite=m.submission!!;assertEquals(TaskStartPhase.REJECTED,noWrite.phase);m.acknowledge(m.control,noWrite);assertTrue(m.canPrepare);assertNull(m.review)
    }
    @Test fun thrownOrCanceledAttemptRetainsSnapshotAfterCloseAndReopen()=runTest {
        val p=Controlled(port().grants);val m=TaskStartModel(p,backgroundScope);val original=source();m.bind(original);m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();p.pending[0].completeExceptionally(CancellationException("synthetic"));job.await()
        val r=m.submission!!;assertEquals(TaskStartPhase.UNKNOWN,r.phase);assertEquals(original,r.attempt.review.source);m.bind(null);assertTrue(m.blocks(context));m.bind(source(revision=2));m.acknowledge(m.control,r);assertTrue(m.blocked);assertEquals(1,m.retainedAttemptCount)
    }
    private inner class Repo:TaskReadRepository {var selected=detail();var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return if(selected.business==business && selected.task.id==id)selected else detail(business,id)}
    }
    private fun origin(allowed:List<TaskDetails>)=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail in allowed}
    @Test fun getWithoutIndependentProvenanceOrStartPortHasNoAction()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,startSubmission=port());val plain=TaskListViewModel(repo)
        try {m.load(101,163);runCurrent();m.open(1101);runCurrent();assertNull(m.startAction!!.source);assertNull(plain.startAction)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun integratedStartSiblingAndResultPreserveSourceAndConsumePeerActions()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),cancelSubmission=FixtureTaskCancelPort(fixture("task-cancel-outcome")),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=port())
        try {m.load(101,164);runCurrent();m.open(1101);runCurrent();val start=m.startAction!!;val before=m.state.detail;val items=m.state.items;val reads=repo.reads
            m.prepareStart(start.control,m.control);val old=start.control!!;m.openComment(start.source!!.read);start.submit(old);assertEquals(0,start.retainedAttemptCount);m.comment!!.close(expected=m.comment!!.returnControl)
            m.prepareStart(start.control,m.control);start.submit(start.control);assertEquals(TaskStartPhase.CONFIRMED,start.submission!!.phase);assertEquals(before,m.state.detail);assertEquals(items,m.state.items);assertEquals(reads,repo.reads)
            start.acknowledge(start.control,start.submission!!);m.prepareCompletion(m.completion!!.control,m.control);m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);m.openCancelReason(start.source!!.read);assertNull(m.completion!!.review);assertNull(m.selfAssignment!!.review);assertNull(m.cancelReason!!.control)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun matchingProgressTerminalReadAndAnotherBusinessRespectRetainedContext()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val original=detail();val progress=original.copy(task=original.task.copy(status="in_progress"));val done=original.copy(task=original.task.copy(status="done"));val p=Controlled(port().grants)
        val m=TaskListViewModel(repo,commentSource=origin(listOf(original,progress,done,detail(202,1201))),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=p)
        try {m.load(101,165);runCurrent();m.open(1101);runCurrent();val start=m.startAction!!;m.prepareStart(start.control,m.control);val job=async {start.submit(start.control)};runCurrent();p.pending[0].complete(SyntheticTaskStartOutcome.Unknown);job.await()
            repo.selected=progress;m.retryDetail(m.detailSelection);runCurrent();m.prepareCompletion(m.completion!!.control,m.control);m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);assertEquals("in_progress",start.source!!.task.status);assertEquals(TaskStartPhase.UNKNOWN,start.submission!!.phase);assertTrue(m.taskActionOccupied);assertNull(m.completion!!.review);assertNull(m.selfAssignment!!.review)
            repo.selected=done;m.retryDetail(m.detailSelection);runCurrent();assertTrue(m.taskActionOccupied);assertEquals(TaskStartPhase.UNKNOWN,start.submission!!.phase)
            m.load(202,166);runCurrent();m.open(1201);runCurrent();assertFalse(m.taskActionOccupied);assertTrue(start.canPrepare);assertTrue(m.startCurrent(m.control));assertEquals(1,start.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class CompleteHeld(override val grants:List<SyntheticTaskCompleteGrant>):SyntheticTaskCompletePort {val pending=mutableListOf<CompletableDeferred<SyntheticTaskCompleteOutcome>>();override suspend fun execute(attempt:TaskCompletionAttempt)=CompletableDeferred<SyntheticTaskCompleteOutcome>().also {pending+=it}.await()}
    private class AssignHeld(override val grants:List<SyntheticTaskSelfAssignGrant>):SyntheticTaskSelfAssignPort {val pending=mutableListOf<CompletableDeferred<SyntheticTaskSelfAssignOutcome>>();override suspend fun execute(attempt:TaskSelfAssignmentAttempt)=CompletableDeferred<SyntheticTaskSelfAssignOutcome>().also {pending+=it}.await()}
    @Test fun hiddenExistingAttemptStillBlocksAfterReadStatusMakesOldSourceIneligible()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {for(assigning in listOf(false,true)) {val repo=Repo();val original=detail();val done=original.copy(task=original.task.copy(status="done"));val c=CompleteHeld(FixtureTaskCompletePort(fixture("task-complete-outcome")).grants);val a=AssignHeld(FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")).grants)
            val m=TaskListViewModel(repo,commentSource=origin(listOf(original,done)),completeSubmission=c,selfAssignSubmission=a,startSubmission=port())
            try {m.load(101,167);runCurrent();m.open(1101);runCurrent();val job=if(assigning) {m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);async {m.selfAssignment!!.submit(m.selfAssignment!!.control)}} else {m.prepareCompletion(m.completion!!.control,m.control);async {m.completion!!.submit(m.completion!!.control)}}
                runCurrent();if(assigning)a.pending[0].complete(SyntheticTaskSelfAssignOutcome.Unknown) else c.pending[0].complete(SyntheticTaskCompleteOutcome.Unknown);job.await();repo.selected=done;m.retryDetail(m.detailSelection);runCurrent()
                assertNull(m.completion!!.source);assertNull(m.selfAssignment!!.source);assertTrue(m.taskActionOccupied);assertTrue(m.hasHiddenRetainedAction);m.prepareStart(m.startAction!!.control,m.control);assertNull(m.startAction!!.review)
            } finally {m.viewModelScope.cancel()}
        }} finally {Dispatchers.resetMain()}
    }
    @Test fun cancellationUnknownAlsoRetainsBarrierWhenItsSourceStatusChanges()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val original=detail();val done=original.copy(task=original.task.copy(status="done"));val cancel=object:SyntheticTaskCancelPort {override val grants=FixtureTaskCancelPort(fixture("task-cancel-outcome")).grants;override suspend fun execute(attempt:TaskCancelAttempt)=SyntheticTaskCancelOutcome.Unknown}
        val m=TaskListViewModel(repo,commentSource=origin(listOf(original,done)),cancelSubmission=cancel,completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=port())
        try {m.load(101,168);runCurrent();m.open(1101);runCurrent();val reason=m.cancelReason!!;m.openCancelReason(reason.state.read!!);reason.update("Manual source reason",reason.inputControl);reason.prepare(reason.control);reason.submit(reason.state.review!!,reason.control);reason.close(expected=reason.returnControl);m.prepareStart(m.startAction!!.control,m.control);assertNull(m.startAction!!.review)
            repo.selected=done;m.retryDetail(m.detailSelection);runCurrent();assertTrue(reason.submissionBlocked);assertTrue(m.hasHiddenRetainedAction);assertFalse(m.startCurrent(m.control));assertEquals(1,reason.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
