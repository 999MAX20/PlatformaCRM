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
class TaskCreateReminderTest {
    private val ctx=TaskDraftContext(101,250)
    private val grant=SyntheticTaskCreateGrant(101,9001,true)
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun catalog()=JSONObject(fixture("task-create-reminder"))
    private fun mode(raw:String)=if(raw=="setDate")TaskDraftDueMode.SET else TaskDraftDueMode.OMIT
    private fun session(r:JSONObject):TaskDraftSession {val s=TaskDraftSession();s.bind(ctx);s.open(ctx);val c=s.state.selection!!;s.update(TaskDraftField.TITLE,"Task",c);s.update(TaskDraftField.DESCRIPTION,"Note",c);s.chooseDue(TaskDraftDueMode.SET,c);s.update(TaskDraftField.DUE_AT,r.getString("due_raw"),c);s.chooseDue(mode(r.getString("due_mode")),c);s.chooseReminder(TaskDraftDueMode.SET,c);s.update(TaskDraftField.REMINDER_AT,r.getString("reminder_raw"),c);s.chooseReminder(mode(r.getString("reminder_mode")),c);s.prepare(c);return s}
    private class Port:SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,true),SyntheticTaskCreateGrant(202,9002,true));val attempts=mutableListOf<TaskCreateAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCreateOutcome>>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskCreateOutcome>().also {pending+=it}.await()}
    }
    private fun base(m:TaskDraftModel) {m.open(m.entryControl);m.update(TaskDraftField.TITLE," Task ",m.inputControl);m.update(TaskDraftField.DESCRIPTION," Note ",m.inputControl)}
    private fun dates(m:TaskDraftModel) {m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2026-10-30T12:00:00Z",m.inputControl);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.REMINDER_AT,"2026-10-30T11:00:00Z",m.inputControl)}
    private fun task(a:TaskCreateAttempt):WorkTask {val v=a.review.preview;return WorkTask(9101,v.title,"open",v.priority,v.dueAt,business=a.authorization.context.business,updatedAt="2026-10-30T12:00:00Z",description=v.description,createdBy=a.authorization.actor,createdAt="2026-10-30T12:00:00Z")}
    @Test fun sharedBodiesOmitEachUnselectedDateAndRetainIndependentRawModes() {
        val rows=catalog().getJSONArray("input_cases");val auth=grant.authorization(ctx)!!
        for(i in 0 until rows.length()) {val r=rows.getJSONObject(i);val s=session(r);val valid=r.getBoolean("valid");assertEquals(r.getString("name"),valid,s.state.phase==TaskDraftPhase.REVIEW);assertEquals(r.getString("due_raw"),s.state.values.dueDate.raw);assertEquals(r.getString("reminder_raw"),s.state.values.reminderDate.raw)
            if(valid){val a=TaskCreateAttemptLedger().begin(s.state.review!!,auth)!!;val b=JSONObject(a.preparedBody()!!);val expected=r.getJSONObject("expected_body");assertEquals(expected.keys().asSequence().toSet(),b.keys().asSequence().toSet());for(k in expected.keys())assertEquals(expected.get(k),b.get(k));assertFalse(b.has("mode"));assertFalse(b.has("snoozed_until"))}else assertTrue(s.state.issues.any {it.problem==TaskDraftProblem.DATE})}
    }
    @Test fun sharedResultsRequireCreateSpecificReminderEvidenceAndBothSelectedInstants() {
        val rows=catalog().getJSONArray("validation_cases");val auth=grant.authorization(ctx)!!
        for(i in 0 until rows.length()) {val r=rows.getJSONObject(i);val review=session(r).state.review!!;val ledger=TaskCreateAttemptLedger();val a=ledger.begin(review,auth)!!;val o=r.getJSONObject("response");val outcome=runCatching<SyntheticTaskCreateOutcome>{SyntheticTaskCreateOutcome.Response(r.getInt("status"),JsonContracts.taskCreateAction(o.toString()),if(r.getBoolean("include_evidence"))o.opt("reminder_at") as? String else null)}.getOrDefault(SyntheticTaskCreateOutcome.Unknown);ledger.complete(a,outcome);val record=ledger.visible(auth)!!;val yes=r.getString("expected")=="confirmed";assertEquals(r.getString("name"),if(yes)TaskCreateAttemptPhase.CONFIRMED else TaskCreateAttemptPhase.UNKNOWN,record.phase);assertEquals(review,record.attempt.review);if(yes && review.preview.reminderAt!=null)assertEquals(o.getString("reminder_at"),record.reminderAt)else assertNull(record.reminderAt);ledger.complete(a,SyntheticTaskCreateOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(yes,ledger.acknowledge(auth));if(!yes)assertTrue(ledger.blocked(ctx.copy(epoch=251)))}
    }
    @Test fun modeSwitchesNeverCopyDatesAndRejectOldInputOrOmittedReview()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);assertEquals(TaskDraftDueDate(),m.state.values.dueDate);assertEquals(TaskDraftDueDate(),m.state.values.reminderDate);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2026-10-30T12:00:00Z",m.inputControl);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.prepare(m.control);assertTrue(m.state.issues.any {it.field==TaskDraftField.REMINDER_AT});assertEquals("",m.state.values.reminderDate.raw)
        val input=m.inputControl;m.update(TaskDraftField.REMINDER_AT,"2026-10-30T11:00:00Z",input);m.chooseReminder(TaskDraftDueMode.OMIT,input);m.update(TaskDraftField.DUE_AT,"stale",input);assertEquals("2026-10-30T12:00:00Z",m.state.values.dueDate.raw);m.prepare(m.control);val omitted=m.state.review!!;assertNull(omitted.preview.reminderAt);m.back(m.returnControl);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.prepare(m.control);m.submit(omitted,m.control);assertTrue(p.attempts.isEmpty());assertEquals("2026-10-30T11:00:00Z",m.state.review!!.preview.reminderAt)
    }
    @Test fun pendingOldCallerWithoutReminderEvidenceBecomesUnknownAndBlocksNewEpoch()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);dates(m);m.prepare(m.control);val review=m.state.review!!;val c=m.control;val j=async {m.submit(review,c)};runCurrent();val pending=m.control;val r=m.submission!!;m.chooseDue(TaskDraftDueMode.OMIT,m.inputControl);m.chooseReminder(TaskDraftDueMode.OMIT,m.inputControl);m.askClear(pending);m.submit(review,pending);m.acknowledge(pending,r);assertEquals(1,p.attempts.size);assertEquals(review.values,m.state.values);p.pending[0].complete(SyntheticTaskCreateOutcome.Response(201,task(p.attempts[0])));j.await();val unknown=m.submission!!;assertEquals(TaskCreateAttemptPhase.UNKNOWN,unknown.phase);assertNull(unknown.reminderAt);assertEquals(review,unknown.attempt.review);m.acknowledge(m.control,unknown);m.bind(ctx.copy(epoch=251));assertTrue(m.submissionBlocked);assertNull(m.submission);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun changedReminderInvalidatesClearAndNoWriteKeepsWholeFormUntilFreshReview()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);dates(m);m.askClear(m.control);val old=m.clearConfirmation!!;m.update(TaskDraftField.REMINDER_AT,"2038-01-19T03:14:08Z",m.inputControl);m.confirmClear(old);assertNull(m.clearConfirmation);assertEquals("2026-10-30T12:00:00Z",m.state.values.dueDate.raw);assertEquals("2038-01-19T03:14:08Z",m.state.values.reminderDate.raw);m.prepare(m.control);val review=m.state.review!!;val c=m.control;val j=async {m.submit(review,c)};runCurrent();p.pending[0].complete(SyntheticTaskCreateOutcome.RejectedWithoutWrite);j.await();m.acknowledge(m.control,m.submission!!);m.submit(review,c);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertEquals(review.values,m.state.values);assertNull(m.state.review);assertEquals(1,p.attempts.size)
    }
    @Test fun lateCompletionCannotChangeOtherBusinessDatesOrControls()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);dates(m);m.prepare(m.control);val j=async {m.submit(m.state.review!!,m.control)};runCurrent();m.bind(TaskDraftContext(202,252));base(m);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.REMINDER_AT,"2038-01-19T03:14:08Z",m.inputControl);val v=m.state.values;val c=m.control;p.pending[0].complete(SyntheticTaskCreateOutcome.Response(201,task(p.attempts[0]),p.attempts[0].review.preview.reminderAt));j.await();assertEquals(v,m.state.values);assertEquals(c,m.control);assertNull(m.submission)
    }
    @Test fun allFiveErrorsAreFieldOwnedAndOmissionDoesNotInventDates() {
        val m=TaskDraftModel();m.bind(ctx);base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.chooseReminder(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.TITLE,"x".repeat(256),m.inputControl);m.update(TaskDraftField.DESCRIPTION,"Bad\u0000text",m.inputControl);m.update(TaskDraftField.PRIORITY,"unsupported",m.inputControl);m.prepare(m.control);assertEquals(TaskDraftField.entries.toSet(),m.state.issues.map {it.field}.toSet());m.update(TaskDraftField.TITLE,"Task",m.inputControl);m.update(TaskDraftField.DESCRIPTION,"Note",m.inputControl);m.update(TaskDraftField.PRIORITY,"normal",m.inputControl);m.chooseDue(TaskDraftDueMode.OMIT,m.inputControl);m.chooseReminder(TaskDraftDueMode.OMIT,m.inputControl);m.prepare(m.control);assertEquals(TaskDraftPhase.REVIEW,m.state.phase);assertNull(m.state.review!!.preview.dueAt);assertNull(m.state.review!!.preview.reminderAt)
    }
    @Test fun confirmedSyntheticBothDatesKeepTaskListAndReadCountUnchanged()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));var reads=0;val repo=object:TaskReadRepository {override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))};override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return JsonContracts.taskDetails(fixture("task-$business-$id"))}}
        val p=object:SyntheticTaskCreatePort {override val grants=listOf(grant);override suspend fun execute(attempt:TaskCreateAttempt)=SyntheticTaskCreateOutcome.Response(201,task(attempt),attempt.review.preview.reminderAt)};val owner=TaskListViewModel(repo,createSubmission=p)
        try {owner.load(101,253);runCurrent();val rows=owner.state.items;val before=reads;val m=owner.draft;base(m);dates(m);m.prepare(m.control);m.submit(m.state.review!!,m.control);assertEquals(TaskCreateAttemptPhase.CONFIRMED,m.submission!!.phase);assertEquals("2026-10-30T12:00:00Z",m.submission!!.task!!.dueAt);assertEquals("2026-10-30T11:00:00Z",m.submission!!.reminderAt);assertEquals(rows,owner.state.items);assertEquals(before,reads)} finally {owner.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
