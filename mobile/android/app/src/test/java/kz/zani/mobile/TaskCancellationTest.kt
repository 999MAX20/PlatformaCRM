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
class TaskCancellationTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val context=TaskCommentContext(101,1101,1)
    private val read=TaskCommentRead(context,1)
    private val grant=SyntheticTaskCancelGrant(101,1101,9001,true)
    private class ControlledPort(update: Boolean=true): SyntheticTaskCancelPort {
        override val grants=listOf(SyntheticTaskCancelGrant(101,1101,9001,update))
        val attempts=mutableListOf<TaskCancelAttempt>();val replies=mutableListOf<CompletableDeferred<SyntheticTaskCancelOutcome>>()
        override suspend fun execute(attempt: TaskCancelAttempt): SyntheticTaskCancelOutcome {attempts+=attempt;val reply=CompletableDeferred<SyntheticTaskCancelOutcome>();replies+=reply;return reply.await()}
    }
    private fun editor(port: SyntheticTaskCancelPort?): Pair<TaskCancelReasonModel,TaskCancelReasonReview> {
        val m=TaskCancelReasonModel(port);m.begin(read);m.receive(true,"open",read);m.open(read);val s=m.state.selection!!;m.update("  Manual reason\n",s);m.prepare(s);return m to m.state.review!!
    }
    private fun response(a: TaskCancelAttempt)=SyntheticTaskCancelOutcome.Response(200,WorkTask(a.authorization.context.task,"Synthetic task","cancelled","normal",null,business=a.authorization.context.business,cancelledAt="2026-10-30T12:00:00Z",cancelledBy=a.authorization.actor,cancelReason=a.review.text,updatedAt="2026-10-30T12:00:00Z"))
    @Test fun existingTaskSerializerFieldsAndCancellationSpecific200AreRequired() {
        val (m,review)=editor(null);val auth=grant.authorization(context)!!;val rows=JSONObject(fixture("task-cancel-outcome")).getJSONArray("validation_cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val ledger=TaskCancelAttemptLedger();val a=ledger.begin(review,m.state.text,"open",auth)!!
            val t=runCatching {JsonContracts.taskCancelAction(row.getJSONObject("response").toString())}.getOrNull()
            ledger.complete(a,if(t!=null)SyntheticTaskCancelOutcome.Response(row.getInt("status"),t) else SyntheticTaskCancelOutcome.Unknown)
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskCancelAttemptPhase.CONFIRMED else TaskCancelAttemptPhase.UNKNOWN,ledger.visible(auth)!!.phase)
            assertEquals("  Manual reason\n",ledger.records[0].attempt.raw)
            if(row.getString("expected")=="unknown") {assertFalse(ledger.acknowledge(auth));assertNull(ledger.begin(review,m.state.text,"open",auth))}
        }
        for(status in listOf("done","cancelled","future_status",""))assertNull(TaskCancelAttemptLedger().begin(review,m.state.text,status,auth))
        assertNull(TaskCancelAttemptLedger().begin(review,"different","open",auth));assertNull(grant.copy(update=false).authorization(context))
    }
    @Test fun staleReviewAndDefaultReadOrDeniedUpdateNeverSubmitCancellation()=runTest {
        for(port in listOf(null,ControlledPort(false))) {val (m,r)=editor(port);m.submit(r);assertEquals(0,m.retainedAttemptCount);assertFalse(m.canSubmit)}
        val p=ControlledPort();val (m,r)=editor(p);m.back(r.selection);m.update("New review",r.selection);m.prepare(r.selection);m.submit(r);assertTrue(p.attempts.isEmpty())
        for(status in listOf("done","cancelled","future_status")) {m.begin(read);m.receive(true,status,read);assertFalse(m.state.available);assertFalse(m.canSubmit)}
    }
    @Test fun pendingDoubleClickBackReopenAndSyntheticResultDoNotChangeSourceTask()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val source=JsonContracts.taskDetails(fixture("task-101-1101"));val before=source.copy()
        val job=launch {m.submit(r)};runCurrent();m.submit(r);m.update("overwrite",r.selection);m.discard(r.selection)
        assertEquals(1,p.attempts.size);assertEquals("  Manual reason\n",m.state.text);assertEquals(TaskCancelAttemptPhase.PENDING,m.submission!!.phase)
        m.back(r.selection);m.open(read);val fresh=m.state.selection!!;p.replies[0].complete(response(p.attempts[0]));job.join()
        assertEquals(TaskCancelAttemptPhase.CONFIRMED,m.submission!!.phase);assertEquals(before,source);assertEquals("open",source.task.status)
        m.acknowledge(r.selection,1);assertNotNull(m.submission);m.acknowledge(fresh,1);assertNull(m.state.selection);assertEquals("",m.state.text);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun reopenedNoWriteErrorReturnsToCurrentEditorThenRequiresNewReview()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].complete(SyntheticTaskCancelOutcome.RejectedWithoutWrite);job.join()
        m.close(r.selection);m.open(read);val fresh=m.state.selection!!;m.acknowledge(fresh,1)
        assertEquals(TaskCommentPhase.EDITING,m.state.phase);assertEquals(fresh,m.state.selection);assertEquals("  Manual reason\n",m.state.text);m.submit(r);assertEquals(1,p.attempts.size)
        m.prepare(fresh);val second=m.state.review!!;val sending=launch {m.submit(second)};runCurrent();assertEquals(2,p.attempts.size);p.replies[1].complete(SyntheticTaskCancelOutcome.Unknown);sending.join()
        m.acknowledge(fresh,1);m.acknowledge(fresh,2);m.discard(fresh);m.submit(second);assertEquals(2,p.attempts.size);assertEquals(TaskCancelAttemptPhase.UNKNOWN,m.submission!!.phase)
    }
    @Test fun lostReplyCancellationAndRereadNeverProveNoWriteOrEnableReplay()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();p.replies[0].completeExceptionally(IllegalStateException("lost reply"));job.join()
        assertEquals(TaskCancelAttemptPhase.UNKNOWN,m.submission!!.phase);m.pause();val newer=read.copy(revision=2);m.begin(newer);m.receive(true,"cancelled",newer)
        assertFalse(m.state.available);assertNull(m.submission);assertEquals(1,m.retainedAttemptCount)
        m.begin(newer);m.receive(true,"open",newer);m.open(newer);assertEquals(TaskCancelAttemptPhase.UNKNOWN,m.submission!!.phase);assertFalse(m.canSubmit)
        val p2=ControlledPort();val (cancelled,c)=editor(p2);val cancelling=launch {cancelled.submit(c)};runCurrent();cancelling.cancelAndJoin();assertEquals(TaskCancelAttemptPhase.UNKNOWN,cancelled.submission!!.phase)
    }
    @Test fun lateBusinessEpochResultHiddenAndSameTargetQuarantined()=runTest {
        val p=ControlledPort();val (m,r)=editor(p);val job=launch {m.submit(r)};runCurrent();m.retainOwner(202,2);val other=TaskCommentRead(TaskCommentContext(202,1201,2),2);m.begin(other);m.receive(true,"open",other)
        p.replies[0].complete(response(p.attempts[0]));job.join();assertNull(m.submission);assertEquals("",m.state.text)
        val epoch=read.copy(context=context.copy(epoch=3),revision=3);m.begin(epoch);m.receive(true,"open",epoch);m.open(epoch);assertNull(m.submission);assertTrue(m.submissionBlocked);assertFalse(m.canSubmit);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun reopenedCommentNoWriteResultAlsoKeepsCurrentEditor()=runTest {
        val port=object: SyntheticTaskCommentPort {
            override val grants=listOf(SyntheticTaskCommentGrant(101,1101,9001,true))
            override suspend fun execute(attempt: TaskCommentAttempt)=SyntheticTaskCommentOutcome.RejectedWithoutWrite
        }
        val m=TaskCommentModel(port);m.begin(read);m.receive(true,read);m.open(read);val s=m.state.selection!!;m.update("Manual comment",s);m.prepare(s);m.submit(m.state.review!!);m.close(s);m.open(read);val fresh=m.state.selection!!;m.acknowledge(fresh,1)
        assertEquals(TaskCommentPhase.EDITING,m.state.phase);assertEquals(fresh,m.state.selection);assertEquals("Manual comment",m.state.text)
    }
}
