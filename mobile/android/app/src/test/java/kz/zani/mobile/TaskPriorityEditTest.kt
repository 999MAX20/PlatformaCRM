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
class TaskPriorityEditTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun port()=FixtureTaskPriorityEditPort(fixture("task-priority-partial-outcome"))
    private val context=TaskCommentContext(101,1101,200)
    private fun source(d:TaskDetails=detail(),epoch:Int=200,revision:Int=1)=TaskPriorityEditSource(TaskCommentRead(TaskCommentContext(d.business,d.task.id,epoch),revision),d.task)
    private class Controlled(override val grants:List<SyntheticTaskPriorityEditGrant>):SyntheticTaskPriorityEditPort {
        val attempts=mutableListOf<TaskPriorityEditAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskPriorityEditOutcome>>()
        override suspend fun execute(attempt:TaskPriorityEditAttempt):SyntheticTaskPriorityEditOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskPriorityEditOutcome>().also {pending+=it}.await()}
    }
    @Test fun exactChoicesAndPartialBodiesNeverDefaultTrimOrIncludeUntouchedFields() {
        assertEquals(listOf("low","normal","high","urgent"),TaskDraftValues.priorities)
        val rows=JSONObject(fixture("task-priority-partial-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val v=TaskPriorityValue.parse(row.getString("raw"));if(row.isNull("expected_body"))assertNull(row.getString("name"),v) else {val b=JSONObject(v!!.body());assertEquals(setOf("priority"),b.keys().asSequence().toSet());assertEquals(row.getString("raw"),b.getString("priority"));assertFalse(b.has("description"));assertFalse(b.has("due_at"))}}
    }
    @Test fun selectedResultRequiresScopeStatusChoiceActualClockAndExactTypes() {
        val rows=JSONObject(fixture("task-priority-partial-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=source(detail().copy(task=detail().task.copy(status=row.getString("source_status"))));val review=TaskPriorityEditReview(s,1,TaskPriorityValue.parse(row.getString("selected"))!!);val ledger=TaskPriorityEditLedger();val a=ledger.begin(review,auth)!!;assertNull(ledger.begin(review,auth));ledger.complete(a,SyntheticTaskPriorityEditOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val r=ledger.visible(auth)!!;val yes=row.getString("expected")=="confirmed";assertEquals(row.getString("name"),if(yes)TaskPriorityEditPhase.CONFIRMED else TaskPriorityEditPhase.UNKNOWN,r.phase);assertEquals(review,r.attempt.review);if(yes)assertEquals(review.value.raw,r.result!!.priority);ledger.complete(a,SyntheticTaskPriorityEditOutcome.RejectedWithoutWrite);assertEquals(r,ledger.visible(auth));assertEquals(yes,ledger.acknowledge(auth))}
    }
    @Test fun independentUpdateAndEligibleStatusAreRequired() {
        val g=SyntheticTaskPriorityEditGrant(101,1101,9001,true);assertNull(g.copy(update=false).authorization(context));assertNull(g.copy(actor=0).authorization(context));assertNull(g.authorization(context.copy(business=202)))
        for(status in listOf("done","cancelled","unknown","")) {val s=source(detail().copy(task=detail().task.copy(status=status)));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(TaskPriorityEditLedger().begin(TaskPriorityEditReview(s,1,TaskPriorityValue.parse("normal")!!),g.authorization(context)!!))}
    }
    @Test fun unsetChoiceAndStaleChoiceReviewBackCannotSubmit()=runTest {
        val p=Controlled(port().grants);val m=TaskPriorityEditModel(p,backgroundScope);m.bind(source());m.open(m.control);m.prepare(m.control);assertTrue(m.showsIssue);assertEquals("",m.raw);assertNull(m.review)
        val unset=m.control;m.choose("high",unset);m.choose("normal",unset);m.choose("high ",m.control);assertEquals("high",m.raw);m.prepare(m.control);val old=m.control;m.back(old);m.submit(old);assertNull(m.review);assertEquals("high",m.raw);assertTrue(p.attempts.isEmpty())
    }
    @Test fun staleResetCannotEraseLaterChoiceAndLocalClearIsNotNullCommand()=runTest {
        val m=TaskPriorityEditModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.choose("high",m.control);m.askClear(m.control);val old=m.clearConfirmation!!;m.dismissClear(old);m.choose("low",m.control);m.confirmClear(old);assertEquals("low",m.raw);m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);m.prepare(m.control);assertEquals("",m.raw);assertNull(m.review);assertEquals(0,m.retainedAttemptCount)
    }
    @Test fun pendingUnknownKeepsExactChoiceSourceAndAttemptAcrossMatchingReread()=runTest {
        val p=Controlled(port().grants);val m=TaskPriorityEditModel(p,backgroundScope);val initial=source();m.bind(initial);m.open(m.control);m.choose("urgent",m.control);m.prepare(m.control);val old=m.control;val job=async {m.submit(old)};runCurrent();val pending=m.control;val r=m.submission!!;m.submit(old);m.submit(pending);m.choose("low",pending);m.askClear(pending);m.back(pending);m.acknowledge(pending,r);assertEquals(1,p.attempts.size);assertEquals("urgent",m.raw);assertEquals(r,m.submission)
        p.pending[0].completeExceptionally(IllegalStateException("synthetic unknown"));job.await();val unknown=m.submission!!;m.bind(source(epoch=201,revision=2));assertTrue(m.blocked);assertNull(m.submission);assertEquals("",m.raw);assertFalse(m.canOpen);m.bind(initial);m.acknowledge(m.control,unknown);assertTrue(m.blocked);assertEquals("urgent",unknown.attempt.review.value.raw);assertEquals(initial,unknown.attempt.review.source)
    }
    @Test fun selectedFakeResultConsumesReadWithoutOptimisticPriorityChange()=runTest {
        val m=TaskPriorityEditModel(port(),backgroundScope);val initial=source();m.bind(initial);m.open(m.control);m.choose("low",m.control);m.prepare(m.control);val old=m.control;m.submit(old);val r=m.submission!!;assertEquals(TaskPriorityEditPhase.CONFIRMED,r.phase);assertEquals("low",r.result!!.priority);assertEquals(initial,m.source);m.acknowledge(m.control,r);m.open(m.control);m.submit(old);assertTrue(m.consumed);assertFalse(m.editing);assertEquals("",m.raw);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun noWritePreservesChoiceAndRequiresFreshReview()=runTest {
        val m=TaskPriorityEditModel(port(),backgroundScope);m.bind(source(detail(101,1401)));m.open(m.control);m.choose("normal",m.control);m.prepare(m.control);val old=m.control;m.submit(old);val r=m.submission!!;assertEquals(TaskPriorityEditPhase.REJECTED,r.phase);m.acknowledge(m.control,r);m.submit(old);assertTrue(m.editing);assertEquals("normal",m.raw);assertNull(m.review);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun lateResultCannotTouchReplacementOwnerOrChoice()=runTest {
        val p=Controlled(port().grants);val m=TaskPriorityEditModel(p,backgroundScope);m.bind(source());m.open(m.control);m.choose("low",m.control);m.prepare(m.control);val send=async {m.submit(m.control)};runCurrent();m.bind(source(detail(202,1201),202));m.open(m.control);m.choose("high",m.control);val next=m.control;p.pending[0].complete(port().execute(p.attempts[0]));send.await();assertEquals(next,m.control);assertNull(m.submission);assertEquals("high",m.raw)
    }
    private inner class Repo:TaskReadRepository {var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return detail(business,id)}
    }
    private fun origin()=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskPriorityEditTest.detail()}
    @Test fun getAndDefaultCompositionCannotGrantUpdate()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,priorityEditSubmission=port());val plain=TaskListViewModel(repo)
        try {m.load(101,203);runCurrent();m.open(1101);runCurrent();assertNull(m.priorityEdit!!.source);assertNull(plain.priorityEdit)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun integratedChooserCommentReturnDatePeerAndFakeResultPreserveGet()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(),dateEditSubmission=FixtureTaskDateEditPort(fixture("task-date-partial-outcome")),priorityEditSubmission=port())
        try {m.load(101,204);runCurrent();m.open(1101);runCurrent();val before=m.state.detail;val items=m.state.items;val reads=repo.reads;val v=m.priorityEdit!!;val old=v.control;m.openDateEdit(m.dateEdit?.control,m.control);m.dateEdit!!.back(m.dateEdit!!.control);m.openPriorityEdit(old,m.control);assertFalse(v.editing)
            m.openPriorityEdit(v.control,m.control);v.choose("urgent",v.control);assertFalse(m.dateEditCurrent(m.control));m.openComment(v.source!!.read);m.comment?.state?.selection?.let {m.comment!!.close(it)};m.openPriorityEdit(v.control,m.control);assertEquals("urgent",v.raw);v.prepare(v.control);val body=JSONObject(v.review!!.value.body());assertEquals(setOf("priority"),body.keys().asSequence().toSet());v.submit(v.control);assertEquals(TaskPriorityEditPhase.CONFIRMED,v.submission!!.phase);assertEquals(before,m.state.detail);assertEquals(items,m.state.items);assertEquals(reads,repo.reads);v.acknowledge(v.control,v.submission!!);m.openDateEdit(m.dateEdit?.control,m.control);assertFalse(m.dateEdit!!.editing);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownPriorityBlocksAllNinePeersAfterNewEpoch()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val p=Controlled(port().grants);val m=TaskListViewModel(repo,commentSource=origin(),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),reopenSubmission=FixtureTaskReopenPort(fixture("task-reopen-outcome")),watcherSubmission=FixtureTaskWatcherPort(fixture("task-watcher-outcome")),undoCancelSubmission=FixtureTaskUndoCancelPort(fixture("task-undo-cancel-outcome")),snoozeSubmission=FixtureTaskSnoozePort(fixture("task-snooze-outcome")),targetAssignSubmission=FixtureTaskAssignPort(fixture("task-assign-outcome")),dateEditSubmission=FixtureTaskDateEditPort(fixture("task-date-partial-outcome")),priorityEditSubmission=p)
        try {m.load(101,205);runCurrent();m.open(1101);runCurrent();val v=m.priorityEdit!!;m.openPriorityEdit(v.control,m.control);v.choose("urgent",v.control);v.prepare(v.control);val job=async {v.submit(v.control)};runCurrent();p.pending[0].complete(SyntheticTaskPriorityEditOutcome.Unknown);job.await();m.load(101,206);runCurrent();m.open(1101);runCurrent();assertTrue(m.taskActionOccupied);assertFalse(m.dateEditCurrent(m.control));assertFalse(m.targetAssignCurrent(m.control));assertFalse(m.snoozeCurrent(m.control));assertFalse(m.startCurrent(m.control));assertFalse(m.completionCurrent(m.control));assertFalse(m.selfAssignmentCurrent(m.control));assertFalse(m.reopenCurrent(m.control));assertFalse(m.watcherCurrent(m.control));assertFalse(m.undoCancelCurrent(m.control));assertNull(v.submission);assertTrue(v.canPresent);assertEquals(1,v.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownDateBlocksIndependentPriorityAfterMatchingReread()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val dates=object:SyntheticTaskDateEditPort {override val grants=FixtureTaskDateEditPort(fixture("task-date-partial-outcome")).grants;override suspend fun execute(attempt:TaskDateEditAttempt)=SyntheticTaskDateEditOutcome.Unknown};val m=TaskListViewModel(repo,commentSource=origin(),dateEditSubmission=dates,priorityEditSubmission=port())
        try {m.load(101,207);runCurrent();m.open(1101);runCurrent();val v=m.dateEdit!!;m.openDateEdit(v.control,m.control);v.select(TaskDateField.DUE,v.control);v.choose(TaskDateMode.CLEAR,v.control);v.prepare(v.control);v.submit(v.control);m.load(101,208);runCurrent();m.open(1101);runCurrent();m.openPriorityEdit(m.priorityEdit?.control,m.control);assertFalse(m.priorityEdit!!.editing);assertTrue(m.taskActionOccupied);assertFalse(m.priorityEditCurrent(m.control))
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
