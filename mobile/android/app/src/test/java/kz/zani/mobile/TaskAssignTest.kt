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
class TaskAssignTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun port()=FixtureTaskAssignPort(fixture("task-assign-outcome"))
    private val context=TaskCommentContext(101,1101,180)
    private fun source(d:TaskDetails=detail(),epoch:Int=180,revision:Int=1)=TaskAssignSource(TaskCommentRead(TaskCommentContext(d.business,d.task.id,epoch),revision),d.task)
    private class Controlled(override val grants:List<SyntheticTaskAssignGrant>):SyntheticTaskAssignPort {
        val attempts=mutableListOf<TaskAssignAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskAssignOutcome>>()
        override suspend fun execute(attempt:TaskAssignAttempt):SyntheticTaskAssignOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskAssignOutcome>().also {pending+=it}.await()}
    }
    @Test fun canonicalTargetInputNeverDefaultsActorOrUnassigns() {
        val rows=JSONObject(fixture("task-assign-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val value=TaskAssignValue.parse(row.getString("raw"));assertEquals(row.getString("name"),if(row.isNull("user_id"))null else row.getLong("user_id"),value?.userID);if(value!=null)assertEquals(row.getString("raw"),value.raw)}
    }
    @Test fun exactResultCasesMatchSelectedMemberAndPreserveStatus() {
        val rows=JSONObject(fixture("task-assign-outcome")).getJSONArray("validation_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val members=row.getJSONArray("eligible_members");val grant=SyntheticTaskAssignGrant(101,1101,9001,true,(0 until members.length()).map {members.getLong(it)});val auth=grant.authorization(context)!!;val s=source(detail().copy(task=detail().task.copy(status=row.getString("source_status"))));val review=TaskAssignReview(s,1,TaskAssignValue.parse(row.getString("input"))!!);val ledger=TaskAssignLedger();val attempt=ledger.begin(review,auth)!!
            assertNull(ledger.begin(review,auth));ledger.complete(attempt,SyntheticTaskAssignOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!;val confirmed=row.getString("expected")=="confirmed";assertEquals(row.getString("name"),if(confirmed)TaskAssignPhase.CONFIRMED else TaskAssignPhase.UNKNOWN,record.phase);if(confirmed){assertEquals(review.value.userID,record.result!!.assignee);assertEquals(s.task.status,record.result!!.status)}
            assertEquals(review,record.attempt.review);ledger.complete(attempt,SyntheticTaskAssignOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(confirmed,ledger.acknowledge(auth))
        }
    }
    @Test fun explicitSyntheticMembershipAndSeparateUpdateAreRequired() {
        val g=SyntheticTaskAssignGrant(101,1101,9001,true,listOf(9003L,9001L));assertNull(g.copy(update=false).authorization(context));assertNull(g.copy(actor=0).authorization(context));assertNull(g.authorization(context.copy(business=202)))
        for(members in listOf(emptyList(),listOf(0L),listOf(-1L),listOf(9003L,9003L)))assertNull(g.copy(eligibleMembers=members).authorization(context))
        val ledger=TaskAssignLedger();assertNull(ledger.begin(TaskAssignReview(source(),1,TaskAssignValue.parse("9999")!!),g.authorization(context)!!))
        for(status in listOf("done","cancelled","unknown","")) {val s=source(detail().copy(task=detail().task.copy(status=status)));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(ledger.begin(TaskAssignReview(s,1,TaskAssignValue.parse("9003")!!),g.authorization(context)!!))}
        val bad=TaskAssignValue.parse("9003")!!.copy(userID=9001);assertNull(ledger.begin(TaskAssignReview(source(),1,bad),g.authorization(context)!!))
    }
    @Test fun targetEditorReviewBackKeepsRawAndRejectsStaleControls()=runTest {
        val p=Controlled(port().grants);val m=TaskAssignModel(p,backgroundScope);m.bind(source());m.open(m.control);val input=m.inputControl;assertEquals("",m.raw);assertEquals(listOf(9003L,9001L),m.eligibleMembers)
        m.update("9999",input);m.prepare(m.control);assertTrue(m.showsIssue);assertNull(m.review);assertEquals("9999",m.raw)
        m.select(9003,m.inputControl);val editing=m.control!!;m.prepare(editing);val old=m.control!!;m.back(old);m.select(9001,input);m.prepare(editing);m.submit(old);assertEquals("9003",m.raw);assertTrue(m.editing);assertNull(m.review);assertTrue(p.attempts.isEmpty())
    }
    @Test fun exactClearCannotBecomeUnassignOrEraseNewSelection()=runTest {
        val m=TaskAssignModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.select(9003,m.inputControl);m.askClear(m.control);val old=m.clearConfirmation!!;m.dismissClear(old);m.select(9001,m.inputControl);m.confirmClear(old);assertEquals("9001",m.raw)
        m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);assertEquals("",m.raw);m.prepare(m.control);assertTrue(m.showsIssue);assertNull(m.review);assertEquals(0,m.retainedAttemptCount)
        m.retainOwner(202,181);m.bind(source(detail(202,1201),181));assertEquals("",m.raw);m.confirmClear(old);assertEquals("",m.raw)
    }
    @Test fun pendingUnknownAndEpochKeepSelectedTargetAttemptWithoutReplay()=runTest {
        val p=Controlled(port().grants);val m=TaskAssignModel(p,backgroundScope);m.bind(source());m.open(m.control);m.select(9003,m.inputControl);m.prepare(m.control);val submit=m.control!!;val job=async {m.submit(submit)};runCurrent();val pending=m.control!!;val record=m.submission!!
        m.submit(submit);m.submit(pending);m.back(pending);m.askClear(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission);assertNull(m.clearConfirmation)
        p.pending[0].completeExceptionally(IllegalStateException("Synthetic unknown"));job.await();val unknown=m.submission!!;assertEquals(TaskAssignPhase.UNKNOWN,unknown.phase);m.bind(source(epoch=181,revision=2));assertTrue(m.blocked);assertNull(m.submission);assertEquals("",m.raw);assertTrue(m.canPresent);assertFalse(m.canOpen);assertEquals("9003",unknown.attempt.review.value.raw)
    }
    @Test fun explicitActorChoiceKeepsOpenAndConfirmedReadIsConsumed()=runTest {
        val m=TaskAssignModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.select(9001,m.inputControl);m.prepare(m.control);val old=m.control!!;m.submit(old);val record=m.submission!!;assertEquals(TaskAssignPhase.CONFIRMED,record.phase);assertEquals(9001L,record.result!!.assignee);assertEquals("open",record.result!!.status)
        m.acknowledge(m.control,record);m.open(m.control);m.submit(old);assertTrue(m.consumed);assertFalse(m.editing);assertEquals(1,m.retainedAttemptCount)
        m.bind(source(detail(101,1401)));m.open(m.control);m.select(9003,m.inputControl);m.prepare(m.control);val rejectedControl=m.control!!;m.submit(rejectedControl);val rejected=m.submission!!;assertEquals(TaskAssignPhase.REJECTED,rejected.phase);m.acknowledge(m.control,rejected);m.submit(rejectedControl);assertNull(m.review);assertTrue(m.editing);assertEquals("9003",m.raw)
    }
    @Test fun lateResultCannotTouchReplacementOwnersTarget()=runTest {
        val p=Controlled(port().grants);val m=TaskAssignModel(p,backgroundScope);m.bind(source());m.open(m.control);m.select(9003,m.inputControl);m.prepare(m.control);val send=async {m.submit(m.control)};runCurrent();m.bind(source(detail(202,1201),182));m.open(m.control);m.select(9004,m.inputControl);val current=m.control
        p.pending[0].complete(port().execute(p.attempts[0]));send.await();assertEquals(current,m.control);assertNull(m.submission);assertEquals("9004",m.raw)
    }
    private inner class Repo:TaskReadRepository {var selected=detail();var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return if(selected.business==business && selected.task.id==id)selected else detail(business,id)}
    }
    private fun origin(allowed:List<TaskDetails>)=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail in allowed}
    @Test fun getWithoutIndependentProvenanceAndDefaultPortsCannotAssign()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,targetAssignSubmission=port());val plain=TaskListViewModel(repo)
        try {m.load(101,183);runCurrent();m.open(1101);runCurrent();assertNull(m.targetAssignment!!.source);assertNull(plain.targetAssignment)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun integratedTargetEditorSnoozePeerAndCommentReturnKeepSourceAndReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),snoozeSubmission=FixtureTaskSnoozePort(fixture("task-snooze-outcome")),targetAssignSubmission=port())
        try {m.load(101,184);runCurrent();m.open(1101);runCurrent();val before=m.state.detail;val rows=m.state.items;val reads=repo.reads;val a=m.targetAssignment!!;val oldEntry=a.control;m.openSnooze(m.snoozeAction?.control,m.control);m.snoozeAction!!.back(m.snoozeAction!!.control);m.openTargetAssign(oldEntry,m.control);assertFalse(a.editing);m.openTargetAssign(a.control,m.control);a.select(9003,a.inputControl);assertFalse(m.snoozeCurrent(m.control));assertFalse(m.completionCurrent(m.control));m.openSnooze(m.snoozeAction?.control,m.control);assertFalse(m.snoozeAction!!.editing);assertTrue(a.editing)
            m.openComment(a.source!!.read);assertFalse(a.editing);m.comment?.state?.selection?.let {m.comment!!.close(it)};m.openTargetAssign(a.control,m.control);assertEquals("9003",a.raw);a.prepare(a.control);a.submit(a.control);assertEquals(TaskAssignPhase.CONFIRMED,a.submission!!.phase);assertEquals(before,m.state.detail);assertEquals(rows,m.state.items);assertEquals(reads,repo.reads)
            a.acknowledge(a.control,a.submission!!);m.openSnooze(m.snoozeAction?.control,m.control);assertFalse(m.snoozeAction!!.editing);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownTargetAssignmentBlocksAllSevenExistingPeersAfterReread()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val p=Controlled(port().grants);val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),reopenSubmission=FixtureTaskReopenPort(fixture("task-reopen-outcome")),watcherSubmission=FixtureTaskWatcherPort(fixture("task-watcher-outcome")),undoCancelSubmission=FixtureTaskUndoCancelPort(fixture("task-undo-cancel-outcome")),snoozeSubmission=FixtureTaskSnoozePort(fixture("task-snooze-outcome")),targetAssignSubmission=p)
        try {m.load(101,185);runCurrent();m.open(1101);runCurrent();val a=m.targetAssignment!!;m.openTargetAssign(a.control,m.control);a.select(9003,a.inputControl);a.prepare(a.control);val send=async {a.submit(a.control)};runCurrent();p.pending[0].complete(SyntheticTaskAssignOutcome.Unknown);send.await();m.load(101,186);runCurrent();m.open(1101);runCurrent()
            assertTrue(m.taskActionOccupied);assertFalse(m.snoozeCurrent(m.control));assertFalse(m.startCurrent(m.control));assertFalse(m.completionCurrent(m.control));assertFalse(m.selfAssignmentCurrent(m.control));assertFalse(m.reopenCurrent(m.control));assertFalse(m.watcherCurrent(m.control));assertFalse(m.undoCancelCurrent(m.control));assertNull(a.submission);assertEquals(1,a.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun snoozeUnknownCannotGrantAssignmentOnMatchingReadOrNewEpoch()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val snooze=object:SyntheticTaskSnoozePort {override val grants=FixtureTaskSnoozePort(fixture("task-snooze-outcome")).grants;override suspend fun execute(attempt:TaskSnoozeAttempt)=SyntheticTaskSnoozeOutcome.Unknown};val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),snoozeSubmission=snooze,targetAssignSubmission=port())
        try {m.load(101,187);runCurrent();m.open(1101);runCurrent();val s=m.snoozeAction!!;m.openSnooze(s.control,m.control);s.update("2026-10-30T12:00:00Z",s.inputControl);s.prepare(s.control);s.submit(s.control);assertEquals(TaskSnoozePhase.UNKNOWN,s.submission!!.phase);m.load(101,188);runCurrent();m.open(1101);runCurrent();m.openTargetAssign(m.targetAssignment?.control,m.control);assertFalse(m.targetAssignment!!.editing);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
