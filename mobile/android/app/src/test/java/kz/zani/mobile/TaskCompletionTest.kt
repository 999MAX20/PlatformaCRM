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
class TaskCompletionTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private val context=TaskCommentContext(101,1101,130)
    private fun source(epoch:Int=130,revision:Int=1)=TaskCompletionSource(TaskCommentRead(context.copy(epoch=epoch),revision),detail().task)
    private fun port()=FixtureTaskCompletePort(fixture("task-complete-outcome"))
    private class Controlled(override val grants:List<SyntheticTaskCompleteGrant>):SyntheticTaskCompletePort {
        val attempts=mutableListOf<TaskCompletionAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCompleteOutcome>>()
        override suspend fun execute(attempt:TaskCompletionAttempt):SyntheticTaskCompleteOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskCompleteOutcome>().also {pending+=it}.await()}
    }
    @Test fun getAndTerminalUnknownStatusNeverGrantCompletionCapability()=runTest {
        assertNull(SyntheticTaskCompleteGrant(101,1101,9001,false).authorization(context));assertNull(SyntheticTaskCompleteGrant(202,1101,9001,true).authorization(context));assertNull(SyntheticTaskCompleteGrant(101,1101,0,true).authorization(context))
        for(status in listOf("done","cancelled","waiting","unknown",""))assertFalse(source().copy(task=detail().task.copy(status=status)).valid)
        assertFalse(source().copy(task=detail().task.copy(business=202)).valid)
        val noGrant=Controlled(emptyList());val model=TaskCompletionModel(noGrant,backgroundScope);model.bind(source());model.prepare(model.control);model.submit(model.control);assertFalse(model.canPresent);assertFalse(model.canPrepare);assertNull(model.review);assertTrue(noGrant.attempts.isEmpty())
    }
    @Test fun strictExistingCompleteResultMatrixRejectsForeignMissingAndMobileProjection() {
        val cases=JSONObject(fixture("task-complete-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val ledger=TaskCompletionLedger();val review=TaskCompletionReview(source(),1);val attempt=ledger.begin(review,auth)!!
            assertNull(ledger.begin(review,auth));ledger.complete(attempt,SyntheticTaskCompleteOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskCompletionPhase.CONFIRMED else TaskCompletionPhase.UNKNOWN,record.phase)
            ledger.complete(attempt,SyntheticTaskCompleteOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));if(record.phase==TaskCompletionPhase.UNKNOWN) {assertFalse(ledger.acknowledge(auth));assertTrue(ledger.blocked(context))}
        }
        assertNull(TaskCompletionResult.decode("[]"));assertNull(TaskCompletionResult.decode("not json"))
    }
    @Test fun unknownRetainsImmutableSnapshotAcrossRereadEpochAndCannotAcknowledge() {
        val ledger=TaskCompletionLedger();val auth=port().grants.firstNotNullOf {it.authorization(context)};val review=TaskCompletionReview(source(),1);val attempt=ledger.begin(review,auth)!!;ledger.complete(attempt,SyntheticTaskCompleteOutcome.Unknown)
        assertEquals(review,ledger.visible(auth)!!.attempt.review);assertNull(ledger.begin(TaskCompletionReview(source(revision=2),2),auth));val newContext=context.copy(epoch=131);val newAuth=port().grants.firstNotNullOf {it.authorization(newContext)}
        assertTrue(ledger.blocked(newContext));assertNull(ledger.visible(newAuth));assertFalse(ledger.acknowledge(newAuth));assertFalse(ledger.acknowledge(auth))
    }
    @Test fun identicalPreviewBackAndPendingDuplicateOrAcknowledgeNeverExecuteAgain()=runTest {
        val p=Controlled(port().grants);val model=TaskCompletionModel(p,backgroundScope);model.bind(source());model.prepare(model.control);val old=model.control!!;model.back(old);model.prepare(model.control);model.submit(old);assertTrue(p.attempts.isEmpty())
        val submit=model.control!!;val job=async {model.submit(submit)};runCurrent();val pending=model.control!!;val record=model.submission!!;model.submit(submit);model.back(pending);model.acknowledge(pending,record)
        assertEquals(1,p.attempts.size);assertEquals(record,model.submission);assertTrue(model.blocked);p.pending[0].completeExceptionally(CancellationException("synthetic"));job.await();assertEquals(TaskCompletionPhase.UNKNOWN,model.submission!!.phase)
        model.bind(null);model.bind(source(revision=2));assertTrue(model.blocked);assertEquals(record.attempt,model.submission!!.attempt);assertFalse(model.canPrepare)
    }
    @Test fun lateCompletionDoesNotChangeNewOwnerAndConfirmedCannotRepeatSameRead()=runTest {
        val fixture=port();val p=Controlled(fixture.grants);val model=TaskCompletionModel(p,backgroundScope);model.bind(source());model.prepare(model.control);val sending=async {model.submit(model.control)};runCurrent()
        val foreign=TaskCompletionSource(TaskCommentRead(TaskCommentContext(202,1201,132),1),detail(202,1201).task);model.bind(foreign);val control=model.control;p.pending[0].complete(fixture.execute(p.attempts[0]));sending.await()
        assertEquals(control,model.control);assertNull(model.submission);assertTrue(model.canPrepare);assertEquals(1,model.retainedAttemptCount)
        model.bind(source());val record=model.submission!!;assertEquals(TaskCompletionPhase.CONFIRMED,record.phase);model.acknowledge(model.control,record);model.prepare(model.control);assertTrue(model.consumed);assertFalse(model.canPrepare);assertNull(model.review);assertEquals("open",model.source!!.task.status)
        model.bind(source(revision=2));assertTrue(model.canPrepare)
    }
    @Test fun rejectedWithoutWriteRequiresFreshExplicitReviewAndOldResultCannotAckIt()=runTest {
        val model=TaskCompletionModel(port(),backgroundScope);val foreign=TaskCompletionSource(TaskCommentRead(TaskCommentContext(202,1201,132),1),detail(202,1201).task);model.bind(foreign);model.prepare(model.control);model.submit(model.control)
        val old=model.control!!;val record=model.submission!!;assertEquals(TaskCompletionPhase.REJECTED,record.phase);model.acknowledge(old,record);assertTrue(model.canPrepare);assertNull(model.review);model.prepare(model.control);val fresh=model.control;model.acknowledge(old,record);assertEquals(fresh,model.control);assertNotEquals(old.review,model.review)
    }
    private inner class Repo:TaskReadRepository {
        var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return detail(business,id)}
    }
    @Test fun taskReadPreviewSiblingAndFakeResultPreserveGetProjectionListAndComments()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val provenance=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskCompletionTest.detail(detail.business,detail.task.id)};val model=TaskListViewModel(repo,commentSource=provenance,completeSubmission=port())
        try {model.load(101,133);runCurrent();model.open(1101);runCurrent();val complete=model.completion!!;val original=model.state.detail;val list=model.state.items;val total=model.state.total;val reads=repo.reads
            assertTrue(complete.canPrepare);complete.prepare(complete.control);val old=complete.control!!;model.openComment(complete.source!!.read);complete.submit(old);assertEquals(0,complete.retainedAttemptCount);assertNull(complete.review)
            model.comment!!.close(expected=model.comment!!.returnControl);complete.prepare(complete.control);complete.submit(complete.control);assertEquals(TaskCompletionPhase.CONFIRMED,complete.submission!!.phase);assertEquals(original,model.state.detail);assertEquals(list,model.state.items);assertEquals(total,model.state.total);assertEquals(reads,repo.reads)
            model.back();assertNull(complete.source);assertEquals(1,complete.retainedAttemptCount)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun completionNeedsIndependentVerifiedFixtureOriginAndIsAbsentWithoutPort()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val model=TaskListViewModel(repo,completeSubmission=port());val plain=TaskListViewModel(repo)
        try {model.load(101,134);runCurrent();model.open(1101);runCurrent();assertNull(model.completion!!.source);assertFalse(model.completion!!.canPrepare);assertNull(plain.completion)} finally {model.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
