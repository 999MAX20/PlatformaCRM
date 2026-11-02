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
class TaskCommentSubmissionTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val context=TaskCommentContext(101,1101,1)
    private val read=TaskCommentRead(context,1)
    private val grant=SyntheticTaskCommentGrant(101,1101,9001,true)
    private fun editor(port: SyntheticTaskCommentPort?): Pair<TaskCommentModel,TaskCommentSelection> {
        val model=TaskCommentModel(port);model.begin(read);model.receive(true,read);model.open(read)
        val selection=model.state.selection!!;model.update("  Manual comment\n",selection);model.prepare(selection);return model to selection
    }
    private class ControlledPort(update: Boolean=true): SyntheticTaskCommentPort {
        override val grants=listOf(SyntheticTaskCommentGrant(101,1101,9001,update))
        val attempts=mutableListOf<TaskCommentAttempt>();val replies=mutableListOf<CompletableDeferred<SyntheticTaskCommentOutcome>>()
        override suspend fun execute(attempt: TaskCommentAttempt): SyntheticTaskCommentOutcome {
            attempts+=attempt;val reply=CompletableDeferred<SyntheticTaskCommentOutcome>();replies+=reply;return reply.await()
        }
    }
    private fun response(attempt: TaskCommentAttempt)=SyntheticTaskCommentOutcome.Response(201,TaskComment(8801,attempt.text,"2026-10-30T12:00:00Z",attempt.authorization.context.task,attempt.authorization.actor,"Synthetic employee","fixture@example.invalid"))

    private suspend fun submitForCheck(model: TaskCommentModel,selection: TaskCommentSelection) {
        val review=model.state.review?.takeIf {it.selection==selection} ?: return;model.submit(review)
    }
    private fun ackForCheck(model: TaskCommentModel,selection: TaskCommentSelection) {model.submission?.let {model.acknowledge(selection,it.attempt.localID)}}

    @Test fun existingActionResponseFieldsValidateTaskActorTextDateAndStatus() {
        val (model,selection)=editor(null);val review=model.state.review!!;val auth=grant.authorization(context)!!
        val rows=JSONObject(fixture("task-comment-submit")).getJSONArray("validation_cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val ledger=TaskCommentAttemptLedger();val attempt=ledger.begin(review,model.state.text,auth)!!
            val parsed=runCatching {JsonContracts.taskCommentAction(row.getJSONObject("response").toString())}.getOrNull()
            ledger.complete(attempt,if(parsed!=null)SyntheticTaskCommentOutcome.Response(row.getInt("status"),parsed) else SyntheticTaskCommentOutcome.Unknown)
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskCommentAttemptPhase.CONFIRMED else TaskCommentAttemptPhase.UNKNOWN,ledger.visible(auth)!!.phase)
            assertEquals("  Manual comment\n",ledger.records[0].attempt.raw)
            ledger.complete(attempt,SyntheticTaskCommentOutcome.RejectedWithoutWrite)
            if(row.getString("expected")=="unknown") {assertFalse(ledger.acknowledge(auth));assertNull(ledger.begin(review,model.state.text,auth))}
        }
        assertEquals(selection,review.selection)
    }
    @Test fun readabilityDoesNotGrantUpdateAndStaleReviewDoesNotSubmit()=runTest {
        for(port in listOf(null,ControlledPort(false))) {
            val (model,s)=editor(port);submitForCheck(model,s);assertFalse(model.canSubmit);assertEquals(0,model.retainedAttemptCount)
        }
        assertNull(grant.authorization(context.copy(business=202)));assertNull(grant.authorization(context.copy(epoch=0)))
        val port=ControlledPort();val (model,s)=editor(port);val oldReview=model.state.review!!;model.back(s);submitForCheck(model,s)
        assertTrue(port.attempts.isEmpty());model.update("New review",s);model.prepare(s);model.submit(oldReview);assertTrue(port.attempts.isEmpty());model.close(s);model.open(read);submitForCheck(model,s);assertTrue(port.attempts.isEmpty())
    }
    @Test fun doubleClickBackReopenAndSafeSuccessPreserveAttemptWithoutAppendingHistory()=runTest {
        val port=ControlledPort();val (model,s)=editor(port);val job=launch {submitForCheck(model,s)};runCurrent()
        submitForCheck(model,s);model.update("overwrite",s);model.discard(s)
        assertEquals(1,port.attempts.size);assertEquals("  Manual comment\n",model.state.text);assertEquals(TaskCommentAttemptPhase.PENDING,model.submission!!.phase)
        model.back(s);assertNull(model.state.selection);model.open(read);val fresh=model.state.selection!!
        ackForCheck(model,s);assertEquals(fresh,model.state.selection)
        port.replies[0].complete(response(port.attempts[0]));job.join()
        assertEquals(TaskCommentAttemptPhase.CONFIRMED,model.submission!!.phase);assertFalse(model.canSubmit)
        ackForCheck(model,s);assertNotNull(model.submission);ackForCheck(model,fresh)
        assertNull(model.state.selection);assertEquals("",model.state.text);assertEquals(1,model.retainedAttemptCount);assertFalse(model.submissionBlocked)
    }
    @Test fun definitiveNoWriteRequiresExplicitEditReviewAndNewAttempt()=runTest {
        val port=ControlledPort();val (model,s)=editor(port);val first=launch {submitForCheck(model,s)};runCurrent();port.replies[0].complete(SyntheticTaskCommentOutcome.RejectedWithoutWrite);first.join()
        submitForCheck(model,s);assertEquals(1,port.attempts.size);ackForCheck(model,s)
        assertEquals(TaskCommentPhase.EDITING,model.state.phase);assertEquals("  Manual comment\n",model.state.text);submitForCheck(model,s);assertEquals(1,port.attempts.size)
        model.prepare(s);val second=launch {submitForCheck(model,s)};runCurrent();assertEquals(2,port.attempts.size);assertNotEquals(port.attempts[0].localID,port.attempts[1].localID)
        port.replies[1].complete(SyntheticTaskCommentOutcome.Unknown);second.join();assertEquals(TaskCommentAttemptPhase.UNKNOWN,model.submission!!.phase)
    }
    @Test fun lostReplyAndCancellationStayUnknownWithRawInputNoClearOrReplay()=runTest {
        val port=ControlledPort();val (model,s)=editor(port);val job=launch {submitForCheck(model,s)};runCurrent();port.replies[0].completeExceptionally(IllegalStateException("lost reply"));job.join()
        assertEquals(TaskCommentAttemptPhase.UNKNOWN,model.submission!!.phase);ackForCheck(model,s);model.discard(s);submitForCheck(model,s)
        assertEquals(1,port.attempts.size);assertEquals("  Manual comment\n",model.state.text)
        model.pause();model.begin(read.copy(revision=2));model.receive(true,read.copy(revision=2));model.open(read.copy(revision=2));submitForCheck(model,model.state.selection!!)
        assertEquals(TaskCommentAttemptPhase.UNKNOWN,model.submission!!.phase);assertEquals(1,port.attempts.size)
        val cancelledPort=ControlledPort();val (cancelled,cs)=editor(cancelledPort);val cancelling=launch {submitForCheck(cancelled,cs)};runCurrent();cancelling.cancelAndJoin()
        assertEquals(TaskCommentAttemptPhase.UNKNOWN,cancelled.submission!!.phase);assertTrue(cancelled.submissionBlocked)
    }
    @Test fun lateContextCannotShowOldSuccessOrResubmitSameTargetInNewEpoch()=runTest {
        val port=ControlledPort();val (model,s)=editor(port);val job=launch {submitForCheck(model,s)};runCurrent()
        model.retainOwner(202,2);val other=TaskCommentRead(TaskCommentContext(202,1201,2),2);model.begin(other);model.receive(true,other)
        port.replies[0].complete(response(port.attempts[0]));job.join()
        assertNull(model.submission);assertEquals("",model.state.text);assertEquals(1,model.retainedAttemptCount)
        val epoch=read.copy(context=context.copy(epoch=3),revision=3);model.begin(epoch);model.receive(true,epoch);model.open(epoch)
        assertNull(model.submission);assertTrue(model.submissionBlocked);assertFalse(model.canSubmit);submitForCheck(model,model.state.selection!!);assertEquals(1,port.attempts.size)
    }
    @Test fun boundedReadWithMatchingTextDoesNotResolveUnknownOutcome() {
        val (model,_)=editor(null);val auth=grant.authorization(context)!!;val ledger=TaskCommentAttemptLedger();val attempt=ledger.begin(model.state.review!!,model.state.text,auth)!!;ledger.complete(attempt,SyntheticTaskCommentOutcome.Unknown)
        val readBack=JsonContracts.taskDetails(fixture("task-101-1101")).copy(comments=listOf(TaskComment(9999,attempt.text,"2026-10-30T12:00:00Z")))
        assertTrue(readBack.validFor(101,1101));assertEquals(TaskCommentAttemptPhase.UNKNOWN,ledger.visible(auth)!!.phase);assertFalse(ledger.acknowledge(auth))
    }
    @Test fun sharedExactRawReviewsAttemptsAndTyped201EchoesKeepUnknownWithoutReplay() {
        val cases=JSONObject(fixture("task-comment-exact-text-cases")).getJSONArray("cases");val auth=grant.authorization(context)!!
        fun reviewed(raw:String):TaskCommentReview {val s=TaskCommentSession();s.begin(read);s.receive(true,read);s.open(read);s.update(raw,s.state.selection!!);s.prepare(s.state.selection!!);return s.state.review!!}
        for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val before=row.getString("before");val after=row.getString("after");val changed=row.getBoolean("changed");val a=reviewed(before);val b=reviewed(after);assertEquals(row.getString("before_preview"),a.text);assertEquals(row.getString("after_preview"),b.text);assertEquals(changed,a!=b);assertEquals(a.selection,b.selection)
            val mismatch=TaskCommentAttemptLedger();assertEquals(changed,mismatch.begin(a,after,auth)==null);val ledger=TaskCommentAttemptLedger();val other=TaskCommentAttemptLedger();val attempt=ledger.begin(a,before,auth)!!;val alternate=other.begin(b,after,auth)!!;assertEquals(changed,attempt!=alternate);assertEquals(before,attempt.raw)
            val echo=JsonContracts.taskCommentAction(row.getString("after_response_json"));val exact=JsonContracts.taskCommentAction(row.getString("before_response_json"));ledger.complete(attempt,SyntheticTaskCommentOutcome.Response(201,echo));assertEquals(if(changed)TaskCommentAttemptPhase.UNKNOWN else TaskCommentAttemptPhase.CONFIRMED,ledger.visible(auth)!!.phase);assertEquals(attempt,ledger.records[0].attempt)
            if(changed){assertFalse(ledger.acknowledge(auth));assertNull(ledger.begin(a,before,auth));ledger.complete(attempt,SyntheticTaskCommentOutcome.Response(201,exact));assertEquals(TaskCommentAttemptPhase.UNKNOWN,ledger.visible(auth)!!.phase);val obj=JSONObject(fixture("task-101-1101"));obj.getJSONArray("comments").getJSONObject(0).put("text",a.text);val reread=JsonContracts.taskDetails(obj.toString());assertTrue(reread.validFor(101,1101));assertEquals(a.text,reread.comments.first().text);assertEquals(TaskCommentAttemptPhase.UNKNOWN,ledger.visible(auth)!!.phase)}
            val positive=TaskCommentAttemptLedger();val exactAttempt=positive.begin(a,before,auth)!!;positive.complete(exactAttempt,SyntheticTaskCommentOutcome.Response(201,exact));assertEquals(TaskCommentAttemptPhase.CONFIRMED,positive.visible(auth)!!.phase);assertEquals(a.text,positive.visible(auth)!!.comment!!.text);assertTrue(positive.acknowledge(auth));assertEquals(before,positive.records[0].attempt.raw)
        }
    }
    @Test fun sharedUnicodeClearReviewAndEchoThroughActualParentRetainUnknownAndExactPositiveResult()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val reference=JsonContracts.taskDetails(fixture("task-101-1101"));val source=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,reference)}
        try {val cases=JSONObject(fixture("task-comment-exact-text-cases")).getJSONArray("cases")
            for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val before=row.getString("before");val after=row.getString("after");val changed=row.getBoolean("changed");val calls=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {r->calls+=r;ReadResponse(200,fixture(if(r.path.endsWith("/1101/"))"task-101-1101" else "tasks-101"))});val port=ControlledPort();val owner=TaskListViewModel(repo,source,port);val epoch=3100+i
                try {owner.load(101,epoch);runCurrent();owner.open(1101);runCurrent();val m=owner.comment!!;val detail=owner.state.detail;val rows=owner.state.items;val reads=calls.toList();owner.openComment(m.state.read!!);val input=m.inputControl!!;m.update(before,input);m.askClear(m.control);val question=m.clearConfirmation!!;m.update(after,input)
                    if(changed){assertNull(m.clearConfirmation);m.confirmClear(question);assertEquals(after,m.state.text);assertEquals(input,m.inputControl);m.askClear(m.control)}else assertEquals(question,m.clearConfirmation)
                    m.confirmClear(m.clearConfirmation!!);assertTrue(m.state.text.isEmpty());assertNull(m.state.selection);owner.openComment(m.state.read!!);m.update(before,m.inputControl);val alternate=TaskCommentReview(m.state.selection!!,TaskCommentText.preview(after));m.prepare(m.control);val review=m.state.review!!;val control=m.control!!
                    if(changed){m.submit(alternate,control);assertTrue(port.attempts.isEmpty());assertTrue(m.canSubmit)};val sending=launch {m.submit(review,control)};runCurrent();val attempt=port.attempts.single();m.update(after,input);m.askClear(m.control);m.confirmClear(question);m.submit(review,control);assertEquals(TaskCommentAttemptPhase.PENDING,m.submission!!.phase);assertTrue(m.submissionBlocked);assertNull(m.clearConfirmation);assertEquals(before,m.state.text)
                    port.replies[0].complete(SyntheticTaskCommentOutcome.Response(201,JsonContracts.taskCommentAction(row.getString("after_response_json"))));runCurrent();sending.join();val record=m.submission!!;assertEquals(if(changed)TaskCommentAttemptPhase.UNKNOWN else TaskCommentAttemptPhase.CONFIRMED,record.phase);assertEquals(attempt,record.attempt);assertEquals(before,record.attempt.raw);assertEquals(review.text,record.attempt.text);assertEquals(reads,calls);assertEquals(detail,owner.state.detail);assertEquals(rows,owner.state.items)
                    if(changed){m.acknowledge(m.control,record);m.discard(m.state.selection!!);m.submit(review,m.control);assertEquals(record,m.submission);assertTrue(m.submissionBlocked);assertEquals(before,m.state.text);assertEquals(1,m.retainedAttemptCount);owner.back();owner.open(1101);runCurrent();owner.openComment(m.state.read!!);assertEquals(record,m.submission);assertEquals(before,m.state.text);m.submit(review,m.control);assertEquals(1,port.attempts.size);owner.load(101,epoch+100);runCurrent();owner.open(1101);runCurrent();owner.openComment(m.state.read!!);assertNull(m.submission);assertTrue(m.submissionBlocked);assertNull(m.inputControl);assertEquals(1,m.retainedAttemptCount)}
                } finally {owner.viewModelScope.cancel()}
                val positiveCalls=mutableListOf<ReadRequest>();val positiveRepo=APIReadRepository(ReadTransport {r->positiveCalls+=r;ReadResponse(200,fixture(if(r.path.endsWith("/1101/"))"task-101-1101" else "tasks-101"))});val positivePort=ControlledPort();val positiveOwner=TaskListViewModel(positiveRepo,source,positivePort)
                try {positiveOwner.load(101,epoch+500);runCurrent();positiveOwner.open(1101);runCurrent();val m=positiveOwner.comment!!;positiveOwner.openComment(m.state.read!!);m.update(before,m.inputControl);m.prepare(m.control);val review=m.state.review!!;val control=m.control!!;val detail=positiveOwner.state.detail;val rows=positiveOwner.state.items;val reads=positiveCalls.toList();val sending=launch {m.submit(review,control)};runCurrent();positivePort.replies[0].complete(SyntheticTaskCommentOutcome.Response(201,JsonContracts.taskCommentAction(row.getString("before_response_json"))));runCurrent();sending.join();val record=m.submission!!;assertEquals(TaskCommentAttemptPhase.CONFIRMED,record.phase);assertEquals(review.text,record.comment!!.text);m.acknowledge(control,record);assertTrue(m.submissionBlocked);m.acknowledge(m.control,record);assertTrue(m.state.text.isEmpty());assertFalse(m.submissionBlocked);assertEquals(1,m.retainedAttemptCount);assertEquals(reads,positiveCalls);assertEquals(detail,positiveOwner.state.detail);assertEquals(rows,positiveOwner.state.items)}finally{positiveOwner.viewModelScope.cancel()}
            }
        } finally {Dispatchers.resetMain()}
    }
}
