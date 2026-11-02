package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskCreateDueTest {
    private val ctx=TaskDraftContext(101,240)
    private val grant=SyntheticTaskCreateGrant(101,9001,true)
    private fun fixture()=JSONObject(javaClass.classLoader!!.getResourceAsStream("fixtures/task-create-due-at.json")!!.bufferedReader().use {it.readText()})
    private fun mode(raw:String)=if(raw=="setDate")TaskDraftDueMode.SET else TaskDraftDueMode.OMIT
    private fun session(mode:TaskDraftDueMode,raw:String):TaskDraftSession {val s=TaskDraftSession();s.bind(ctx);s.open(ctx);val c=s.state.selection!!;s.update(TaskDraftField.TITLE,"Task",c);s.update(TaskDraftField.DESCRIPTION,"Note",c);s.chooseDue(TaskDraftDueMode.SET,c);s.update(TaskDraftField.DUE_AT,raw,c);s.chooseDue(mode,c);s.prepare(c);return s}
    private class Port:SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,true),SyntheticTaskCreateGrant(202,9002,true));val attempts=mutableListOf<TaskCreateAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCreateOutcome>>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskCreateOutcome>().also {pending+=it}.await()}
    }
    private fun base(m:TaskDraftModel) {m.open(m.entryControl);m.update(TaskDraftField.TITLE," Task ",m.inputControl);m.update(TaskDraftField.DESCRIPTION," Note ",m.inputControl)}
    @Test fun sharedOptionalInputBodiesDistinguishOmissionAndExplicitNonNullSet() {
        val rows=fixture().getJSONArray("input_cases");val auth=grant.authorization(ctx)!!
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=session(mode(row.getString("mode")),row.getString("raw"));val valid=row.getBoolean("valid");assertEquals(valid,s.state.phase==TaskDraftPhase.REVIEW);assertEquals(row.getString("raw"),s.state.values.dueDate.raw)
            if(valid){val a=TaskCreateAttemptLedger().begin(s.state.review!!,auth)!!;val b=JSONObject(a.preparedBody()!!);val expected=row.getJSONObject("expected_body");assertEquals(expected.keys().asSequence().toSet(),b.keys().asSequence().toSet());for(k in expected.keys())assertEquals(expected.get(k),b.get(k));assertFalse(b.has("mode"));assertFalse(b.has("reminder_at"));assertFalse(b.has("snoozed_until"))}else assertTrue(s.state.issues.contains(TaskDraftIssue(TaskDraftField.DUE_AT,TaskDraftProblem.DATE)))}
    }
    @Test fun sharedSelectedResultsRequireNonNullMatchingInstantAndKeepExistingCreateGuards() {
        val rows=fixture().getJSONArray("validation_cases");val auth=grant.authorization(ctx)!!
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val review=session(mode(row.getString("mode")),row.getString("raw")).state.review!!;val ledger=TaskCreateAttemptLedger();val a=ledger.begin(review,auth)!!;val outcome=runCatching<SyntheticTaskCreateOutcome>{SyntheticTaskCreateOutcome.Response(row.getInt("status"),JsonContracts.taskCreateAction(row.getJSONObject("response").toString()))}.getOrDefault(SyntheticTaskCreateOutcome.Unknown);ledger.complete(a,outcome);val r=ledger.visible(auth)!!;val yes=row.getString("expected")=="confirmed";assertEquals(row.getString("name"),if(yes)TaskCreateAttemptPhase.CONFIRMED else TaskCreateAttemptPhase.UNKNOWN,r.phase);assertEquals(review,r.attempt.review);ledger.complete(a,SyntheticTaskCreateOutcome.RejectedWithoutWrite);assertEquals(r,ledger.visible(auth));assertEquals(yes,ledger.acknowledge(auth));if(!yes)assertTrue(ledger.blocked(ctx.copy(epoch=241)))}
    }
    @Test fun modeChangesRejectOldInputRetainRawAndInvalidateOldReview()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);assertEquals(TaskDraftDueDate(),m.state.values.dueDate);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.prepare(m.control);assertTrue(m.state.issues.any {it.field==TaskDraftField.DUE_AT});val input=m.inputControl;m.update(TaskDraftField.DUE_AT,"2000-02-29T00:00:00Z",input);m.update(TaskDraftField.DUE_AT,"2026-10-30T17:00:00+05:00",input);m.chooseDue(TaskDraftDueMode.OMIT,input);m.update(TaskDraftField.DUE_AT,"stale",input);assertEquals("2026-10-30T17:00:00+05:00",m.state.values.dueDate.raw);m.prepare(m.control);val omitted=m.state.review!!;assertNull(omitted.preview.dueAt);m.back(m.returnControl);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.prepare(m.control);m.submit(omitted,m.control);assertTrue(p.attempts.isEmpty());assertEquals("2026-10-30T17:00:00+05:00",m.state.review!!.preview.dueAt)
    }
    @Test fun pendingUnknownKeepsCompleteRawFormAndBlocksSameBusinessNewEpoch()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2000-02-29T00:00:00Z",m.inputControl);m.prepare(m.control);val review=m.state.review!!;val send=m.control;val job=async {m.submit(review,send)};runCurrent();val pending=m.control;val record=m.submission!!;m.chooseDue(TaskDraftDueMode.OMIT,m.inputControl);m.update(TaskDraftField.DUE_AT,"lost",m.inputControl);m.askClear(pending);m.submit(review,pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(review.values,m.state.values);val b=JSONObject(p.attempts[0].preparedBody()!!);assertEquals(setOf("business","title","description","priority","due_at"),b.keys().asSequence().toSet());p.pending[0].complete(SyntheticTaskCreateOutcome.Unknown);job.await();val unknown=m.submission!!;m.acknowledge(m.control,unknown);m.bind(ctx.copy(epoch=241));assertTrue(m.submissionBlocked);assertNull(m.submission);assertEquals(review,unknown.attempt.review);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun noWriteRequiresFreshReviewAndExactClearQuestionCannotEraseChangedDate()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2000-02-29T00:00:00Z",m.inputControl);m.askClear(m.control);val old=m.clearConfirmation!!;m.update(TaskDraftField.DUE_AT,"2038-01-19T03:14:08Z",m.inputControl);m.confirmClear(old);assertNull(m.clearConfirmation);assertEquals("2038-01-19T03:14:08Z",m.state.values.dueDate.raw);m.prepare(m.control);val review=m.state.review!!;val c=m.control;val j=async {m.submit(review,c)};runCurrent();p.pending[0].complete(SyntheticTaskCreateOutcome.RejectedWithoutWrite);j.await();m.acknowledge(m.control,m.submission!!);m.submit(review,c);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertEquals(review.values,m.state.values);assertNull(m.state.review);assertEquals(1,p.attempts.size)
    }
    @Test fun lateCompletionCannotTouchReplacementBusinessDueDateOrCurrentControls()=runTest {
        val p=Port();val m=TaskDraftModel(p);m.bind(ctx);base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2026-10-30T12:00:00Z",m.inputControl);m.prepare(m.control);val j=async {m.submit(m.state.review!!,m.control)};runCurrent();m.bind(TaskDraftContext(202,242));base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.DUE_AT,"2038-01-19T03:14:08Z",m.inputControl);val v=m.state.values;val c=m.control;p.pending[0].complete(SyntheticTaskCreateOutcome.Unknown);j.await();assertEquals(v,m.state.values);assertEquals(c,m.control);assertNull(m.submission)
    }
    @Test fun allFourFieldErrorsAreOwnedAndOmissionRestoresValidScalarReviewWithoutDateDefault() {
        val m=TaskDraftModel();m.bind(ctx);base(m);m.chooseDue(TaskDraftDueMode.SET,m.inputControl);m.update(TaskDraftField.TITLE,"x".repeat(256),m.inputControl);m.update(TaskDraftField.DESCRIPTION,"Bad\u0000text",m.inputControl);m.update(TaskDraftField.PRIORITY,"unsupported",m.inputControl);m.prepare(m.control);assertEquals(TaskDraftField.entries.filterNot {it==TaskDraftField.REMINDER_AT}.toSet(),m.state.issues.map {it.field}.toSet());assertEquals(TaskDraftDueMode.OMIT,m.state.values.reminderDate.mode);m.update(TaskDraftField.TITLE,"Task",m.inputControl);m.update(TaskDraftField.DESCRIPTION,"Note",m.inputControl);m.update(TaskDraftField.PRIORITY,"normal",m.inputControl);m.chooseDue(TaskDraftDueMode.OMIT,m.inputControl);m.prepare(m.control);assertEquals(TaskDraftPhase.REVIEW,m.state.phase);assertNull(m.state.review!!.preview.dueAt);assertEquals("",m.state.values.dueDate.raw)
    }
}
