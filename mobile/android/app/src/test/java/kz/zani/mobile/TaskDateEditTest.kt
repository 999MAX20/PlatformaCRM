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
class TaskDateEditTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun port()=FixtureTaskDateEditPort(fixture("task-date-partial-outcome"))
    private fun field(raw:String)=TaskDateField.entries.single {it.wire==raw}
    private fun mode(raw:String)=if(raw=="set")TaskDateMode.SET else TaskDateMode.CLEAR
    private val context=TaskCommentContext(101,1101,190)
    private fun source(d:TaskDetails=detail(),epoch:Int=190,revision:Int=1)=TaskDateEditSource(TaskCommentRead(TaskCommentContext(d.business,d.task.id,epoch),revision),d.task)
    private class Controlled(override val grants:List<SyntheticTaskDateEditGrant>):SyntheticTaskDateEditPort {
        val attempts=mutableListOf<TaskDateEditAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskDateEditOutcome>>()
        override suspend fun execute(attempt:TaskDateEditAttempt):SyntheticTaskDateEditOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskDateEditOutcome>().also {pending+=it}.await()}
    }
    @Test fun sharedInputBodiesContainOnlyOneSelectedExistingKey() {
        val rows=JSONObject(fixture("task-date-partial-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val change=TaskDateChange(field(row.getString("field")),mode(row.getString("mode")),row.getString("raw"));val body=change.body()
            if(row.isNull("expected_body")){assertNull(row.getString("name"),body);assertFalse(change.valid)} else {val actual=JSONObject(body!!);assertEquals(1,actual.length());assertEquals(setOf(change.field.wire),actual.keys().asSequence().toSet());val expected=row.getJSONObject("expected_body");assertEquals(expected.get(change.field.wire),actual.get(change.field.wire));assertFalse(actual.has("description"));assertFalse(actual.has("snoozed_until"))}
        }
    }
    @Test fun fieldAndModeHaveNoDefaultsAndEachRawInputSurvivesSwitches() {
        var d=TaskDateDraft();assertNull(d.field);assertNull(d.mode);assertNull(d.change);d=d.select(TaskDateField.DUE);assertNull(d.change);d=d.choose(TaskDateMode.SET).update("2026-10-30T12:00:00Z");val due=d.change
        d=d.select(TaskDateField.REMINDER);assertNull(d.mode);assertEquals("",d.raw);d=d.choose(TaskDateMode.CLEAR).update("retained unused");assertEquals(TaskDateMode.CLEAR,d.change!!.mode);d=d.select(TaskDateField.DUE);assertEquals(due,d.change)
    }
    @Test fun selectedResultLensDistinguishesNullMissingOtherFieldAndMalformedResponse() {
        val rows=JSONObject(fixture("task-date-partial-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=source(detail().copy(task=detail().task.copy(status=row.getString("source_status"))));val change=TaskDateChange(field(row.getString("field")),mode(row.getString("mode")),row.getString("raw"));val review=TaskDateEditReview(s,1,change);val ledger=TaskDateEditLedger();val a=ledger.begin(review,auth)!!;assertNull(ledger.begin(review,auth));ledger.complete(a,SyntheticTaskDateEditOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!;val confirmed=row.getString("expected")=="confirmed"
            assertEquals(row.getString("name"),if(confirmed)TaskDateEditPhase.CONFIRMED else TaskDateEditPhase.UNKNOWN,record.phase);assertEquals(review,record.attempt.review);if(confirmed){assertEquals(change.field,record.result!!.field);assertTrue(record.result!!.matches(change))};ledger.complete(a,SyntheticTaskDateEditOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(confirmed,ledger.acknowledge(auth))
        }
    }
    @Test fun eligibilityAndIndependentUpdateAreRequired() {
        val g=SyntheticTaskDateEditGrant(101,1101,9001,true);assertNull(g.copy(update=false).authorization(context));assertNull(g.copy(actor=0).authorization(context));assertNull(g.authorization(context.copy(business=202)))
        for(status in listOf("done","cancelled","unknown","")) {val s=source(detail().copy(task=detail().task.copy(status=status)));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(TaskDateEditLedger().begin(TaskDateEditReview(s,1,TaskDateChange(TaskDateField.DUE,TaskDateMode.CLEAR,"")),g.authorization(context)!!))}
    }
    @Test fun capturedFieldModeInputReviewBackRejectOldCallbacks()=runTest {
        val p=Controlled(port().grants);val m=TaskDateEditModel(p,backgroundScope);m.bind(source());m.open(m.control);m.prepare(m.control);assertTrue(m.showsIssue);assertNull(m.draft.field);assertNull(m.review)
        m.select(TaskDateField.DUE,m.control);m.choose(TaskDateMode.SET,m.control);val dueInput=m.inputControl;m.update("2026-10-30T12:00:00Z",dueInput);m.select(TaskDateField.REMINDER,m.control);m.choose(TaskDateMode.CLEAR,m.control);m.update("stale",dueInput);assertEquals("",m.draft.raw)
        m.select(TaskDateField.DUE,m.control);val editor=m.control!!;assertEquals("2026-10-30T12:00:00Z",m.draft.raw);m.prepare(editor);val old=m.control!!;m.back(old);m.update("stale",dueInput);m.prepare(editor);m.submit(old);assertNull(m.review);assertTrue(p.attempts.isEmpty());assertEquals(editor.draft,m.draft)
    }
    @Test fun oldDraftClearCannotEraseNewFieldAndClearDraftDoesNotMakeNullCommand()=runTest {
        val m=TaskDateEditModel(port(),backgroundScope);m.bind(source());m.open(m.control);m.select(TaskDateField.DUE,m.control);m.choose(TaskDateMode.CLEAR,m.control);m.askClear(m.control);val old=m.clearConfirmation!!;m.dismissClear(old);m.select(TaskDateField.REMINDER,m.control);m.confirmClear(old);assertEquals(TaskDateField.REMINDER,m.draft.field)
        m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);m.prepare(m.control);assertNull(m.draft.field);assertNull(m.draft.mode);assertNull(m.review);assertEquals(0,m.retainedAttemptCount)
    }
    @Test fun pendingUnknownRetainsFieldModeRawSourceAcrossNewEpochWithoutRetry()=runTest {
        val p=Controlled(port().grants);val m=TaskDateEditModel(p,backgroundScope);m.bind(source());m.open(m.control);m.select(TaskDateField.DUE,m.control);m.choose(TaskDateMode.SET,m.control);m.update("2000-02-29T00:00:00Z",m.inputControl);m.prepare(m.control);val submit=m.control!!;val job=async {m.submit(submit)};runCurrent();val pending=m.control!!;val record=m.submission!!
        m.submit(submit);m.submit(pending);m.back(pending);m.select(TaskDateField.REMINDER,pending);m.askClear(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission);assertNull(m.clearConfirmation)
        p.pending[0].completeExceptionally(IllegalStateException("synthetic unknown"));job.await();val unknown=m.submission!!;m.bind(source(epoch=191,revision=2));assertTrue(m.blocked);assertNull(m.submission);assertNull(m.draft.field);assertFalse(m.canOpen);assertEquals(TaskDateField.DUE,unknown.attempt.review.change.field);assertEquals(TaskDateMode.SET,unknown.attempt.review.change.mode);assertEquals("2000-02-29T00:00:00Z",unknown.attempt.review.change.raw)
    }
    @Test fun selectedNullFakeResultConsumesReadWithoutChangingSourceDates()=runTest {
        val m=TaskDateEditModel(port(),backgroundScope);val original=detail();m.bind(source(original));m.open(m.control);m.select(TaskDateField.DUE,m.control);m.choose(TaskDateMode.CLEAR,m.control);m.prepare(m.control);val old=m.control!!;m.submit(old);val record=m.submission!!;assertEquals(TaskDateEditPhase.CONFIRMED,record.phase);assertEquals(TaskDateField.DUE,record.result!!.field);assertNull(record.result!!.value);assertNotNull(original.task.dueAt);assertEquals(TaskScheduleValue.NotSet,original.reminderAt)
        m.acknowledge(m.control,record);m.open(m.control);m.submit(old);assertTrue(m.consumed);assertFalse(m.editing);assertEquals(1,m.retainedAttemptCount)
        m.bind(source(detail(101,1401)));m.open(m.control);m.select(TaskDateField.REMINDER,m.control);m.choose(TaskDateMode.CLEAR,m.control);m.prepare(m.control);val rejectedControl=m.control!!;m.submit(rejectedControl);val rejected=m.submission!!;m.acknowledge(m.control,rejected);m.submit(rejectedControl);assertTrue(m.editing);assertNull(m.review);assertEquals(TaskDateField.REMINDER,m.draft.field);assertEquals(TaskDateMode.CLEAR,m.draft.mode)
    }
    @Test fun lateResultCannotTouchReplacementOwnersFieldOrInput()=runTest {
        val p=Controlled(port().grants);val m=TaskDateEditModel(p,backgroundScope);m.bind(source());m.open(m.control);m.select(TaskDateField.DUE,m.control);m.choose(TaskDateMode.CLEAR,m.control);m.prepare(m.control);val send=async {m.submit(m.control)};runCurrent();m.bind(source(detail(202,1201),192));m.open(m.control);m.select(TaskDateField.REMINDER,m.control);m.choose(TaskDateMode.SET,m.control);m.update("2038-01-19T03:14:08Z",m.inputControl);val replacement=m.control
        p.pending[0].complete(port().execute(p.attempts[0]));send.await();assertEquals(replacement,m.control);assertNull(m.submission);assertEquals("2038-01-19T03:14:08Z",m.draft.raw)
    }
    private inner class Repo:TaskReadRepository {var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return detail(business,id)}
    }
    private fun origin()=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskDateEditTest.detail()}
    @Test fun getWithoutProvenanceAndDefaultPortsCannotEditDates()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,dateEditSubmission=port());val plain=TaskListViewModel(repo)
        try {m.load(101,193);runCurrent();m.open(1101);runCurrent();assertNull(m.dateEdit!!.source);assertNull(plain.dateEdit)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun integratedOneFieldBodyPeersCommentReturnAndResultKeepAllSourceFields()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(),snoozeSubmission=FixtureTaskSnoozePort(fixture("task-snooze-outcome")),targetAssignSubmission=FixtureTaskAssignPort(fixture("task-assign-outcome")),dateEditSubmission=port())
        try {m.load(101,194);runCurrent();m.open(1101);runCurrent();val before=m.state.detail;val rows=m.state.items;val reads=repo.reads;val d=m.dateEdit!!;val oldEntry=d.control;m.openTargetAssign(m.targetAssignment?.control,m.control);m.targetAssignment!!.back(m.targetAssignment!!.control);m.openDateEdit(oldEntry,m.control);assertFalse(d.editing)
            m.openDateEdit(d.control,m.control);d.select(TaskDateField.REMINDER,d.control);d.choose(TaskDateMode.SET,d.control);d.update("2026-10-30T17:00:00+05:00",d.inputControl);assertFalse(m.snoozeCurrent(m.control));assertFalse(m.targetAssignCurrent(m.control));m.openComment(d.source!!.read);m.comment?.state?.selection?.let {m.comment!!.close(it)};m.openDateEdit(d.control,m.control);assertEquals(TaskDateField.REMINDER,d.draft.field);assertEquals("2026-10-30T17:00:00+05:00",d.draft.raw)
            d.prepare(d.control);val body=JSONObject(d.review!!.change.body()!!);assertEquals(setOf("reminder_at"),body.keys().asSequence().toSet());assertFalse(body.has("description"));assertFalse(body.has("due_at"));d.submit(d.control);assertEquals(TaskDateEditPhase.CONFIRMED,d.submission!!.phase);assertEquals(before,m.state.detail);assertEquals(rows,m.state.items);assertEquals(reads,repo.reads)
            d.acknowledge(d.control,d.submission!!);m.openSnooze(m.snoozeAction?.control,m.control);m.openTargetAssign(m.targetAssignment?.control,m.control);assertFalse(m.snoozeAction!!.editing);assertFalse(m.targetAssignment!!.editing);assertTrue(m.taskActionOccupied)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownDateBlocksAllEightExistingActionPeersAfterReread()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val p=Controlled(port().grants);val m=TaskListViewModel(repo,commentSource=origin(),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),reopenSubmission=FixtureTaskReopenPort(fixture("task-reopen-outcome")),watcherSubmission=FixtureTaskWatcherPort(fixture("task-watcher-outcome")),undoCancelSubmission=FixtureTaskUndoCancelPort(fixture("task-undo-cancel-outcome")),snoozeSubmission=FixtureTaskSnoozePort(fixture("task-snooze-outcome")),targetAssignSubmission=FixtureTaskAssignPort(fixture("task-assign-outcome")),dateEditSubmission=p)
        try {m.load(101,197);runCurrent();m.open(1101);runCurrent();val d=m.dateEdit!!;m.openDateEdit(d.control,m.control);d.select(TaskDateField.DUE,d.control);d.choose(TaskDateMode.CLEAR,d.control);d.prepare(d.control);val send=async {d.submit(d.control)};runCurrent();p.pending[0].complete(SyntheticTaskDateEditOutcome.Unknown);send.await();m.load(101,198);runCurrent();m.open(1101);runCurrent()
            assertTrue(m.taskActionOccupied);assertFalse(m.targetAssignCurrent(m.control));assertFalse(m.snoozeCurrent(m.control));assertFalse(m.startCurrent(m.control));assertFalse(m.completionCurrent(m.control));assertFalse(m.selfAssignmentCurrent(m.control));assertFalse(m.reopenCurrent(m.control));assertFalse(m.watcherCurrent(m.control));assertFalse(m.undoCancelCurrent(m.control));assertNull(d.submission);assertEquals(1,d.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownTargetAssignmentBlocksIndependentDateFieldAfterMatchingReread()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val assign=object:SyntheticTaskAssignPort {override val grants=FixtureTaskAssignPort(fixture("task-assign-outcome")).grants;override suspend fun execute(attempt:TaskAssignAttempt)=SyntheticTaskAssignOutcome.Unknown};val m=TaskListViewModel(repo,commentSource=origin(),targetAssignSubmission=assign,dateEditSubmission=port())
        try {m.load(101,195);runCurrent();m.open(1101);runCurrent();val a=m.targetAssignment!!;m.openTargetAssign(a.control,m.control);a.select(9003,a.inputControl);a.prepare(a.control);a.submit(a.control);m.load(101,196);runCurrent();m.open(1101);runCurrent();m.openDateEdit(m.dateEdit?.control,m.control);assertFalse(m.dateEdit!!.editing);assertTrue(m.taskActionOccupied);assertFalse(m.dateEditCurrent(m.control))
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
