package kz.zani.mobile

import kotlinx.coroutines.test.runTest
import kz.zani.mobile.core.*
import kz.zani.mobile.ui.*
import kz.zani.mobile.data.JsonContracts
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class TaskCreateExactTextTest {
    private fun fixture()=JSONObject(javaClass.classLoader!!.getResourceAsStream("fixtures/task-create-exact-text.json")!!.bufferedReader().use {it.readText()})
    private val context=TaskDraftContext(101,230)
    private val grant=SyntheticTaskCreateGrant(101,9001,true)
    private fun values(o:JSONObject)=TaskDraftValues(o.getString("title"),o.getString("description"),o.getString("priority"))
    private fun review(v:TaskDraftValues):TaskDraftReview {val s=TaskDraftSession();s.bind(context);s.open(context);val c=s.state.selection!!;s.update(TaskDraftField.TITLE,v.title,c);s.update(TaskDraftField.DESCRIPTION,v.description,c);s.update(TaskDraftField.PRIORITY,v.priority,c);assertTrue(s.prepare(c));return s.state.review!!}
    private class Port(private val outcome:SyntheticTaskCreateOutcome):SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,true));val attempts=mutableListOf<TaskCreateAttempt>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {attempts+=attempt;return outcome}
    }
    @Test fun sharedCreateResponsesMatchExactReviewedTextWithoutUnicodeConversion() {
        val rows=fixture().getJSONArray("cases");val auth=grant.authorization(context)!!
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val review=review(values(row.getJSONObject("raw")));val expected=row.getString("expected")=="confirmed";val ledger=TaskCreateAttemptLedger();val a=ledger.begin(review,auth)!!;val outcome=runCatching<SyntheticTaskCreateOutcome> {SyntheticTaskCreateOutcome.Response(row.getInt("status"),JsonContracts.taskCreateAction(row.getJSONObject("response").toString()))}.getOrDefault(SyntheticTaskCreateOutcome.Unknown);ledger.complete(a,outcome);val record=ledger.visible(auth)!!;assertEquals(row.getString("name"),if(expected)TaskCreateAttemptPhase.CONFIRMED else TaskCreateAttemptPhase.UNKNOWN,record.phase);assertEquals(review,record.attempt.review);ledger.complete(a,SyntheticTaskCreateOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));assertEquals(expected,ledger.acknowledge(auth))}
    }
    @Test fun rawSnapshotAndPreviewEqualityKeepDifferentCanonicalSpellingsDistinct() {
        val rows=fixture().getJSONArray("snapshot_cases")
        for(i in 0 until rows.length()) {val r=rows.getJSONObject(i);val a=values(r.getJSONObject("left"));val b=values(r.getJSONObject("right"));assertEquals(r.getBoolean("raw_equal"),a==b);assertEquals(r.getBoolean("preview_equal"),a.preview==b.preview)}
    }
    @Test fun inconsistentCanonicallyEquivalentPreviewCannotBeginCreateAttempt() {
        val source=review(TaskDraftValues(title="e\u0301",description="s\u0301"));val auth=grant.authorization(context)!!
        assertNull(TaskCreateAttemptLedger().begin(source.copy(preview=source.preview.copy(title="é")),auth));assertNull(TaskCreateAttemptLedger().begin(source.copy(preview=source.preview.copy(description="ś")),auth))
    }
    @Test fun changedCanonicalRawInvalidatesOldClearConfirmationInBothFields() {
        val rows=fixture().getJSONArray("snapshot_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val a=values(row.getJSONObject("left"));val b=values(row.getJSONObject("right"));val m=TaskDraftModel();m.bind(context);m.open(m.entryControl);m.update(TaskDraftField.TITLE,a.title,m.inputControl);m.update(TaskDraftField.DESCRIPTION,a.description,m.inputControl);m.askClear(m.control);val question=m.clearConfirmation!!;val field=if(row.getString("field")=="title")TaskDraftField.TITLE else TaskDraftField.DESCRIPTION;m.update(field,if(field==TaskDraftField.TITLE)b.title else b.description,m.inputControl);m.confirmClear(question);assertNull(m.clearConfirmation);assertNotNull(m.state.selection);assertEquals(b,m.state.values)}
    }
    @Test fun oldReviewCannotSubmitUnderCurrentVisitDespiteCanonicalEquivalence()=runTest {
        val p=Port(SyntheticTaskCreateOutcome.RejectedWithoutWrite);val m=TaskDraftModel(p);m.bind(context);m.open(m.entryControl);m.update(TaskDraftField.TITLE," e\u0301 ",m.inputControl);m.update(TaskDraftField.DESCRIPTION," s\u0301 ",m.inputControl);m.prepare(m.control);val old=m.state.review!!;m.back(m.returnControl);m.update(TaskDraftField.TITLE," é ",m.inputControl);m.update(TaskDraftField.DESCRIPTION," ś ",m.inputControl);m.prepare(m.control);val current=m.state.review!!;m.submit(old,m.control);assertTrue(p.attempts.isEmpty());assertNull(m.submission);assertEquals(current,m.state.review)
        m.submit(current,m.control);val r=m.submission!!;assertEquals(1,p.attempts.size);assertEquals(TaskCreateAttemptPhase.REJECTED,r.phase);m.acknowledge(m.control,r);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertEquals(current.values,m.state.values);assertNull(m.state.review)
    }
    @Test fun differentlySpelledReturnedTextRemainsUnknownAfterNewEpochWithoutRetry()=runTest {
        val row=fixture().getJSONArray("cases").getJSONObject(1);val p=Port(SyntheticTaskCreateOutcome.Response(201,JsonContracts.taskCreateAction(row.getJSONObject("response").toString())));val m=TaskDraftModel(p);m.bind(context);m.open(m.entryControl);val v=values(row.getJSONObject("raw"));m.update(TaskDraftField.TITLE,v.title,m.inputControl);m.update(TaskDraftField.DESCRIPTION,v.description,m.inputControl);m.update(TaskDraftField.PRIORITY,v.priority,m.inputControl);m.prepare(m.control);val review=m.state.review!!;m.submit(review,m.control);val unknown=m.submission!!;assertEquals(TaskCreateAttemptPhase.UNKNOWN,unknown.phase);assertEquals(review,unknown.attempt.review);m.acknowledge(m.control,unknown);m.bind(context.copy(epoch=231));assertTrue(m.submissionBlocked);assertNull(m.submission);assertEquals(1,m.retainedAttemptCount);assertEquals(1,p.attempts.size)
    }
    @Test fun exactPrecomposedRepresentationStillConfirmsAndRetainsOriginalReview() {
        val row=fixture().getJSONArray("cases").getJSONObject(5);val r=review(values(row.getJSONObject("raw")));val auth=grant.authorization(context)!!;val ledger=TaskCreateAttemptLedger();val a=ledger.begin(r,auth)!!;ledger.complete(a,SyntheticTaskCreateOutcome.Response(201,JsonContracts.taskCreateAction(row.getJSONObject("response").toString())));assertEquals(TaskCreateAttemptPhase.CONFIRMED,ledger.visible(auth)!!.phase);assertEquals(r,ledger.visible(auth)!!.attempt.review)
    }
}
