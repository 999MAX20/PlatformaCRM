package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskCreationTest {
    private val context=TaskDraftContext(101,1)
    private class ControlledPort(create:Boolean=true):SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,create),SyntheticTaskCreateGrant(202,9002,create))
        val attempts=mutableListOf<TaskCreateAttempt>();val replies=mutableListOf<CompletableDeferred<SyntheticTaskCreateOutcome>>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {attempts+=attempt;val r=CompletableDeferred<SyntheticTaskCreateOutcome>();replies+=r;return r.await()}
    }
    private fun editor(port:SyntheticTaskCreatePort?):Pair<TaskDraftModel,TaskDraftReview> {
        val m=TaskDraftModel(port);m.bind(context);m.open(context);val s=m.state.selection!!;m.update(TaskDraftField.TITLE,"  Manual task\n",s);m.update(TaskDraftField.DESCRIPTION,"  Manual description\n",s);m.update(TaskDraftField.PRIORITY,"high",s);m.prepare(s);return m to m.state.review!!
    }
    private fun response(a:TaskCreateAttempt):SyntheticTaskCreateOutcome {val v=a.review.preview;return SyntheticTaskCreateOutcome.Response(201,WorkTask(88001,v.title,"open",v.priority,null,business=a.authorization.context.business,updatedAt="2026-10-30T12:00:00Z",description=v.description,createdBy=a.authorization.actor,createdAt="2026-10-30T12:00:00Z"))}
    private fun fixture()=javaClass.classLoader!!.getResourceAsStream("fixtures/task-create-outcome.json")!!.bufferedReader().use {it.readText()}
    @Test fun existingCreate201FieldsValidateBusinessCreatorAndExactNormalizedPreview() {
        val (m,r)=editor(null);val auth=SyntheticTaskCreateGrant(101,9001,true).authorization(context)!!;val rows=JSONObject(fixture()).getJSONArray("validation_cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val l=TaskCreateAttemptLedger();val a=l.begin(r,auth)!!;val t=runCatching {JsonContracts.taskCreateAction(row.getJSONObject("response").toString())}.getOrNull()
            l.complete(a,if(t!=null)SyntheticTaskCreateOutcome.Response(row.getInt("status"),t) else SyntheticTaskCreateOutcome.Unknown)
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskCreateAttemptPhase.CONFIRMED else TaskCreateAttemptPhase.UNKNOWN,l.visible(auth)!!.phase)
            assertEquals("  Manual task\n",l.records[0].attempt.review.values.title);assertEquals("Manual task",l.records[0].attempt.review.preview.title)
            if(row.getString("expected")=="unknown") {assertFalse(l.acknowledge(auth));assertNull(l.begin(r,auth))}
        }
        assertNull(TaskCreateAttemptLedger().begin(r.copy(preview=r.preview.copy(title="other")),auth));assertFalse(m.canSubmit)
    }
    @Test fun noCreateCapabilityAndStaleOrInvalidReviewCannotInvokePort()=runTest {
        for(p in listOf(null,ControlledPort(false))) {val (m,r)=editor(p);m.submit(r);assertEquals(0,m.retainedAttemptCount);assertFalse(m.canSubmit)}
        val p=ControlledPort();val (m,r)=editor(p);m.back(r.selection);m.update(TaskDraftField.TITLE,"Changed",r.selection);m.prepare(r.selection);m.submit(r);assertTrue(p.attempts.isEmpty())
        m.back(r.selection);m.update(TaskDraftField.DESCRIPTION,"Bad\u0000desc",r.selection);m.prepare(r.selection);m.submit(r);assertTrue(p.attempts.isEmpty());assertEquals(TaskDraftPhase.EDITING,m.state.phase)
    }
    @Test fun pendingDoubleClickBackReopenAndSyntheticResultRetainRawWithoutRealCreation()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();m.submit(r);m.update(TaskDraftField.TITLE,"overwrite",r.selection);m.discard(r.selection)
        assertEquals(1,p.attempts.size);assertEquals(r.values,m.state.values);assertEquals(TaskCreateAttemptPhase.PENDING,m.submission!!.phase)
        m.back(r.selection);m.open(context);val fresh=m.state.selection!!;p.replies[0].complete(response(p.attempts[0]));job.join()
        assertEquals(TaskCreateAttemptPhase.CONFIRMED,m.submission!!.phase);assertEquals(9001,m.submission!!.task!!.createdBy);m.acknowledge(r.selection,1);assertNotNull(m.submission)
        m.acknowledge(fresh,1);assertEquals(TaskDraftValues(),m.state.values);assertNull(m.state.selection);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun reopenedNoWriteErrorReturnsToEditorAndNewAttemptNeedsExplicitReview()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].complete(SyntheticTaskCreateOutcome.RejectedWithoutWrite);job.join()
        m.close(r.selection);m.open(context);val fresh=m.state.selection!!;m.acknowledge(fresh,1);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertEquals(fresh,m.state.selection);assertEquals(r.values,m.state.values)
        m.submit(r);assertEquals(1,p.attempts.size);m.prepare(fresh);val next=m.state.review!!;val second=launch {m.submit(next)};runCurrent();assertEquals(2,p.attempts.size);p.replies[1].complete(SyntheticTaskCreateOutcome.Unknown);second.join()
        m.acknowledge(fresh,1);m.acknowledge(fresh,2);m.discard(fresh);m.submit(next);assertEquals(2,p.attempts.size);assertEquals(TaskCreateAttemptPhase.UNKNOWN,m.submission!!.phase)
    }
    @Test fun lostReplyAndCancellationRetainUnknownWithoutRereadMatchingOrRetry()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].completeExceptionally(IllegalStateException("lost reply"));job.join();assertEquals(TaskCreateAttemptPhase.UNKNOWN,m.submission!!.phase)
        m.close(r.selection);m.open(context);assertEquals(r.values,m.state.values);assertFalse(m.canSubmit);m.submit(r);assertEquals(1,p.attempts.size)
        val p2=ControlledPort();val (cancelled,c)=editor(p2);val cancelling=launch {cancelled.submit(c)};runCurrent();cancelling.cancelAndJoin();assertEquals(TaskCreateAttemptPhase.UNKNOWN,cancelled.submission!!.phase)
    }
    @Test fun lateBusinessEpochHidesOldResultAndOnlySameBusinessTargetIsQuarantined()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();m.bind(TaskDraftContext(202,2));p.replies[0].complete(response(p.attempts[0]));job.join()
        assertNull(m.submission);assertEquals(TaskDraftValues(),m.state.values);assertFalse(m.submissionBlocked);assertEquals(1,m.retainedAttemptCount)
        m.bind(context.copy(epoch=3));m.open(context.copy(epoch=3));assertNull(m.submission);assertTrue(m.submissionBlocked);assertFalse(m.canSubmit)
    }
}
