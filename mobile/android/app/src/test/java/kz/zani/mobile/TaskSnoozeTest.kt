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
class TaskSnoozeTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun port()=FixtureTaskSnoozePort(fixture("task-snooze-outcome"))
    private val context=TaskCommentContext(101,1101,170)
    private fun source(d:TaskDetails=detail(),epoch:Int=170,revision:Int=1)=TaskSnoozeSource(TaskCommentRead(TaskCommentContext(d.business,d.task.id,epoch),revision),d.task,d.reminderAt)
    private class Controlled(override val grants:List<SyntheticTaskSnoozeGrant>):SyntheticTaskSnoozePort {
        val attempts=mutableListOf<TaskSnoozeAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskSnoozeOutcome>>()
        override suspend fun execute(attempt:TaskSnoozeAttempt):SyntheticTaskSnoozeOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskSnoozeOutcome>().also {pending+=it}.await()}
    }
    @Test fun explicitOffsetCalendarAndPrecisionInputsUseSharedIndependentOracle() {
        val rows=JSONObject(fixture("task-snooze-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val value=TaskSnoozeValue.parse(row.getString("raw"));assertEquals(row.getString("name"),if(row.isNull("microseconds"))null else row.getLong("microseconds"),value?.microseconds);if(value!=null)assertEquals(row.getString("raw"),value.raw)}
    }
    @Test fun exactResultCasesPreserveStatusDeadlineReminderAndInputInstant() {
        val rows=JSONObject(fixture("task-snooze-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val reminder=when {row.isNull("source_reminder")->TaskScheduleValue.NotSet;row.get("source_reminder") is String->TaskScheduleValue.At(row.getString("source_reminder"));else->TaskScheduleValue.Unknown}
            val d=detail();val s=source(d.copy(task=d.task.copy(status=row.getString("source_status")),reminderAt=reminder));val review=TaskSnoozeReview(s,1,TaskSnoozeValue.parse(row.getString("input"))!!);val ledger=TaskSnoozeLedger();val a=ledger.begin(review,auth)!!;assertNull(ledger.begin(review,auth))
            ledger.complete(a,SyntheticTaskSnoozeOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!;assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskSnoozePhase.CONFIRMED else TaskSnoozePhase.UNKNOWN,record.phase);assertEquals(review,record.attempt.review);ledger.complete(a,SyntheticTaskSnoozeOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(record.phase==TaskSnoozePhase.CONFIRMED,ledger.acknowledge(auth))
        }
    }
    @Test fun sourceStatusAndIndependentUpdateAreRequiredWithoutInventedMemberFlag() {
        val g=SyntheticTaskSnoozeGrant(101,1101,9001,true);assertNull(g.copy(update=false).authorization(context));assertNull(g.copy(actor=0).authorization(context));assertNull(g.authorization(context.copy(business=202)))
        for(status in listOf("done","cancelled","unknown","")) {val s=source(detail().copy(task=detail().task.copy(status=status)));assertTrue(s.identityValid);assertFalse(s.valid);val ledger=TaskSnoozeLedger();assertNull(ledger.begin(TaskSnoozeReview(s,1,TaskSnoozeValue.parse("2026-10-30T12:00:00Z")!!),g.authorization(context)!!))}
    }
    @Test fun rawInputReviewBackAndStaleCallbacksKeepExactText()=runTest {
        val p=Controlled(port().grants);val m=TaskSnoozeModel(p,backgroundScope);m.bind(source());m.open(m.control);val input=m.inputControl;assertEquals("",m.raw)
        m.update(" 2026-10-30T12:00:00Z",input);m.prepare(m.control);assertTrue(m.showsIssue);assertNull(m.review);assertTrue(m.raw.startsWith(" "))
        m.update("2026-10-30T17:00:00.123456+05:00",m.inputControl);val editing=m.control!!;m.prepare(editing);val old=m.control!!;m.back(old);m.update("old",input);m.prepare(editing);m.submit(old)
        assertEquals(editing.raw,m.raw);assertTrue(m.editing);assertNull(m.review);assertTrue(p.attempts.isEmpty());m.back(m.control);m.open(m.control);assertEquals(editing.raw,m.raw);assertNotEquals(input,m.inputControl)
    }
    @Test fun clearQuestionCannotEraseEditedOrForeignRaw()=runTest {
        val m=TaskSnoozeModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.update("raw",m.inputControl);m.askClear(m.control);val old=m.clearConfirmation!!;m.dismissClear(old);m.update("new",m.inputControl);m.confirmClear(old);assertEquals("new",m.raw)
        m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);assertEquals("",m.raw);assertTrue(m.editing);m.update("private",m.inputControl);m.retainOwner(202,171);m.bind(source(detail(202,1201),171));assertEquals("",m.raw);m.confirmClear(old);assertEquals("",m.raw)
    }
    @Test fun pendingUnknownAndNewEpochKeepSourceInputAndAttemptWithoutRetry()=runTest {
        val p=Controlled(port().grants);val m=TaskSnoozeModel(p,backgroundScope);val initial=source();m.bind(initial);m.open(m.control);m.update("2000-02-29T00:00:00Z",m.inputControl);m.prepare(m.control);val submit=m.control!!;val job=async {m.submit(submit)};runCurrent();val pending=m.control!!;val record=m.submission!!
        m.submit(submit);m.submit(pending);m.back(pending);m.askClear(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission);assertNull(m.clearConfirmation)
        p.pending[0].completeExceptionally(IllegalStateException("Synthetic unknown"));job.await();val unknown=m.submission!!;assertEquals(TaskSnoozePhase.UNKNOWN,unknown.phase);m.bind(source(epoch=171,revision=2));assertTrue(m.blocked);assertNull(m.submission);assertEquals("",m.raw);assertTrue(m.canPresent);assertFalse(m.canOpen);assertEquals("2000-02-29T00:00:00Z",unknown.attempt.review.value.raw)
    }
    @Test fun explicitProducerEchoConfirmedConsumptionAndNoWriteNeedFreshReview()=runTest {
        val m=TaskSnoozeModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.update("2000-02-29T00:00:00Z",m.inputControl);m.prepare(m.control);val old=m.control!!;m.submit(old);val record=m.submission!!;assertEquals(TaskSnoozePhase.CONFIRMED,record.phase);assertEquals("2000-02-29T00:00:00Z",record.result!!.snoozedUntil);assertEquals(TaskScheduleValue.NotSet,m.source!!.let {detail().snoozedUntil})
        m.acknowledge(m.control,record);m.open(m.control);m.submit(old);assertTrue(m.consumed);assertFalse(m.editing);assertEquals(1,m.retainedAttemptCount)
        m.bind(source(detail(101,1401)));m.open(m.control);m.update("2026-10-30T12:00:00Z",m.inputControl);m.prepare(m.control);val rejectedControl=m.control!!;m.submit(rejectedControl);val rejected=m.submission!!;assertEquals(TaskSnoozePhase.REJECTED,rejected.phase);m.acknowledge(m.control,rejected);m.submit(rejectedControl);assertNull(m.review);assertTrue(m.editing);assertEquals(rejected.attempt.review.value.raw,m.raw)
    }
    @Test fun lateOutcomeCannotTouchReplacementOwnerInput()=runTest {
        val p=Controlled(port().grants);val m=TaskSnoozeModel(p,backgroundScope);m.bind(source());m.open(m.control);m.update("2026-10-30T12:00:00Z",m.inputControl);m.prepare(m.control);val send=async {m.submit(m.control)};runCurrent()
        m.bind(source(detail(202,1201),172));m.open(m.control);m.update("2038-01-19T03:14:08Z",m.inputControl);val foreign=m.control;p.pending[0].complete(port().execute(p.attempts[0]));send.await();assertEquals(foreign,m.control);assertNull(m.submission);assertEquals("2038-01-19T03:14:08Z",m.raw)
    }
    private inner class Repo:TaskReadRepository {var selected=detail();var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return if(selected.business==business && selected.task.id==id)selected else detail(business,id)}
    }
    private fun origin(allowed:List<TaskDetails>)=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail in allowed}
    @Test fun getWithoutProvenanceAndDefaultPortsCannotOfferSnooze()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,snoozeSubmission=port());val plain=TaskListViewModel(repo)
        try {m.load(101,173);runCurrent();m.open(1101);runCurrent();assertNull(m.snoozeAction!!.source);assertNull(plain.snoozeAction)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun integratedRawEditorPeersCommentReturnAndResultKeepSourceAndReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),snoozeSubmission=port())
        try {m.load(101,174);runCurrent();m.open(1101);runCurrent();val before=m.state.detail;val rows=m.state.items;val reads=repo.reads;val s=m.snoozeAction!!;m.openSnooze(s.control,m.control);s.update("2026-10-30T12:00:00Z",s.inputControl)
            assertFalse(m.startCurrent(m.control));assertFalse(m.completionCurrent(m.control));m.prepareStart(m.startAction?.control,m.control);assertNull(m.startAction?.review);assertTrue(s.editing)
            m.openComment(s.source!!.read);assertFalse(s.editing);m.comment?.state?.selection?.let {m.comment!!.close(it)};m.openSnooze(s.control,m.control);assertEquals("2026-10-30T12:00:00Z",s.raw);s.prepare(s.control);s.submit(s.control);assertEquals(TaskSnoozePhase.CONFIRMED,s.submission!!.phase);assertEquals(before,m.state.detail);assertEquals(rows,m.state.items);assertEquals(reads,repo.reads)
            s.acknowledge(s.control,s.submission!!);m.prepareStart(m.startAction?.control,m.control);assertNull(m.startAction?.review);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownSnoozeQuarantinesEveryLifecyclePeerAfterRereadAndEpoch()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val p=Controlled(port().grants);val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),snoozeSubmission=p)
        try {m.load(101,175);runCurrent();m.open(1101);runCurrent();val s=m.snoozeAction!!;m.openSnooze(s.control,m.control);s.update("2026-10-30T12:00:00Z",s.inputControl);s.prepare(s.control);val send=async {s.submit(s.control)};runCurrent();p.pending[0].complete(SyntheticTaskSnoozeOutcome.Unknown);send.await();m.load(101,176);runCurrent();m.open(1101);runCurrent()
            assertTrue(m.taskActionOccupied);assertFalse(m.startCurrent(m.control));assertFalse(m.completionCurrent(m.control));assertFalse(m.selfAssignmentCurrent(m.control));assertFalse(m.reopenCurrent(m.control));assertFalse(m.watcherCurrent(m.control));assertFalse(m.undoCancelCurrent(m.control));assertFalse(s.canOpen);assertNull(s.submission);assertEquals(1,s.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun allSixExistingUnknownActionLedgersBlockSnoozeOnMatchingOpenRead()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            for(kind in 0..5) {
                val repo=Repo();val original=detail();val first=original.copy(task=original.task.copy(status=when(kind){4->"done";5->"cancelled";else->"open"}));repo.selected=first
                val m=TaskListViewModel(repo,commentSource=origin(listOf(original,first)),snoozeSubmission=port(),
                    completeSubmission=if(kind==0)object:SyntheticTaskCompletePort {override val grants=listOf(SyntheticTaskCompleteGrant(101,1101,9001,true));override suspend fun execute(attempt:TaskCompletionAttempt)=SyntheticTaskCompleteOutcome.Unknown}else null,
                    selfAssignSubmission=if(kind==1)object:SyntheticTaskSelfAssignPort {override val grants=listOf(SyntheticTaskSelfAssignGrant(101,1101,9001,true,true));override suspend fun execute(attempt:TaskSelfAssignmentAttempt)=SyntheticTaskSelfAssignOutcome.Unknown}else null,
                    startSubmission=if(kind==2)object:SyntheticTaskStartPort {override val grants=listOf(SyntheticTaskStartGrant(101,1101,9001,true));override suspend fun execute(attempt:TaskStartAttempt)=SyntheticTaskStartOutcome.Unknown}else null,
                    watcherSubmission=if(kind==3)object:SyntheticTaskWatcherPort {override val grants=listOf(SyntheticTaskWatcherGrant(101,1101,9001,true,true));override suspend fun execute(attempt:TaskWatcherAttempt)=SyntheticTaskWatcherOutcome.Unknown}else null,
                    reopenSubmission=if(kind==4)object:SyntheticTaskReopenPort {override val grants=listOf(SyntheticTaskReopenGrant(101,1101,9001,true));override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}else null,
                    undoCancelSubmission=if(kind==5)object:SyntheticTaskUndoCancelPort {override val grants=listOf(SyntheticTaskUndoCancelGrant(101,1101,9001,true));override suspend fun execute(attempt:TaskUndoCancelAttempt)=SyntheticTaskUndoCancelOutcome.Unknown}else null)
                try {m.load(101,177);runCurrent();m.open(1101);runCurrent()
                    when(kind) {0->{m.prepareCompletion(m.completion?.control,m.control);m.completion!!.submit(m.completion!!.control)};1->{m.prepareSelfAssignment(m.selfAssignment?.control,m.control);m.selfAssignment!!.submit(m.selfAssignment!!.control)};2->{m.prepareStart(m.startAction?.control,m.control);m.startAction!!.submit(m.startAction!!.control)};3->{m.prepareWatcher(m.watcherAction?.control,m.control);m.watcherAction!!.submit(m.watcherAction!!.control)};4->{m.prepareReopen(m.reopenAction?.control,m.control);m.reopenAction!!.submit(m.reopenAction!!.control)};else->{m.prepareUndoCancel(m.undoCancelAction?.control,m.control);m.undoCancelAction!!.submit(m.undoCancelAction!!.control)}}
                    repo.selected=original;m.load(101,178);runCurrent();m.open(1101);runCurrent();m.openSnooze(m.snoozeAction?.control,m.control);assertFalse("peer $kind",m.snoozeAction!!.editing);assertTrue("peer $kind",m.taskActionOccupied)
                } finally {m.viewModelScope.cancel()}
            }
        } finally {Dispatchers.resetMain()}
    }
}
