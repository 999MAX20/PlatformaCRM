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
class TaskSelfAssignmentTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private val context=TaskCommentContext(101,1101,130)
    private fun source(epoch:Int=130,revision:Int=1)=TaskSelfAssignmentSource(TaskCommentRead(context.copy(epoch=epoch),revision),detail().task)
    private fun port()=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome"))
    private class Controlled(override val grants:List<SyntheticTaskSelfAssignGrant>):SyntheticTaskSelfAssignPort {
        val attempts=mutableListOf<TaskSelfAssignmentAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskSelfAssignOutcome>>()
        override suspend fun execute(attempt:TaskSelfAssignmentAttempt):SyntheticTaskSelfAssignOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskSelfAssignOutcome>().also {pending+=it}.await()}
    }
    @Test fun getAndTerminalUnknownStatusNeverGrantCompletionCapability()=runTest {
        assertNull(SyntheticTaskSelfAssignGrant(101,1101,9001,false,true).authorization(context));assertNull(SyntheticTaskSelfAssignGrant(202,1101,9001,true,true).authorization(context));assertNull(SyntheticTaskSelfAssignGrant(101,1101,0,true,true).authorization(context))
        assertNull(SyntheticTaskSelfAssignGrant(101,1101,9001,true,false).authorization(context))
        for(status in listOf("done","cancelled","waiting","unknown",""))assertFalse(source().copy(task=detail().task.copy(status=status)).valid)
        assertFalse(source().copy(task=detail().task.copy(business=202)).valid)
        val badMember=JSONObject(fixture("task-self-assign-outcome"));badMember.getJSONArray("scenarios").getJSONObject(0).getJSONObject("grant").put("active_member","true");assertTrue(FixtureTaskSelfAssignPort(badMember.toString()).grants.isEmpty())
        val badFixture=JSONObject(fixture("task-self-assign-outcome")).put("fixture_only","true");assertTrue(FixtureTaskSelfAssignPort(badFixture.toString()).grants.isEmpty())
        val noGrant=Controlled(emptyList());val model=TaskSelfAssignmentModel(noGrant,backgroundScope);model.bind(source());model.prepare(model.control);model.submit(model.control);assertFalse(model.canPresent);assertFalse(model.canPrepare);assertNull(model.review);assertTrue(noGrant.attempts.isEmpty())
    }
    @Test fun strictExistingCompleteResultMatrixRejectsForeignMissingAndMobileProjection() {
        val cases=JSONObject(fixture("task-self-assign-outcome")).getJSONArray("validation_cases");val auth=port().grants.firstNotNullOf {it.authorization(context)}
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val ledger=TaskSelfAssignmentLedger();val review=TaskSelfAssignmentReview(source(),1);val attempt=ledger.begin(review,auth)!!
            assertNull(ledger.begin(review,auth));ledger.complete(attempt,SyntheticTaskSelfAssignOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(auth)!!
            assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskSelfAssignmentPhase.CONFIRMED else TaskSelfAssignmentPhase.UNKNOWN,record.phase)
            ledger.complete(attempt,SyntheticTaskSelfAssignOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(auth));if(record.phase==TaskSelfAssignmentPhase.UNKNOWN) {assertFalse(ledger.acknowledge(auth));assertTrue(ledger.blocked(context))}
        }
        assertNull(TaskSelfAssignmentResult.decode("[]"));assertNull(TaskSelfAssignmentResult.decode("not json"))
    }
    @Test fun unknownRetainsImmutableSnapshotAcrossRereadEpochAndCannotAcknowledge() {
        val ledger=TaskSelfAssignmentLedger();val auth=port().grants.firstNotNullOf {it.authorization(context)};val review=TaskSelfAssignmentReview(source(),1);val attempt=ledger.begin(review,auth)!!;ledger.complete(attempt,SyntheticTaskSelfAssignOutcome.Unknown)
        assertEquals(review,ledger.visible(auth)!!.attempt.review);assertNull(ledger.begin(TaskSelfAssignmentReview(source(revision=2),2),auth));val newContext=context.copy(epoch=131);val newAuth=port().grants.firstNotNullOf {it.authorization(newContext)}
        assertTrue(ledger.blocked(newContext));assertNull(ledger.visible(newAuth));assertFalse(ledger.acknowledge(newAuth));assertFalse(ledger.acknowledge(auth))
    }
    @Test fun identicalPreviewBackAndPendingDuplicateOrAcknowledgeNeverExecuteAgain()=runTest {
        val p=Controlled(port().grants);val model=TaskSelfAssignmentModel(p,backgroundScope);model.bind(source());model.prepare(model.control);val old=model.control!!;model.back(old);model.prepare(model.control);model.submit(old);assertTrue(p.attempts.isEmpty())
        val submit=model.control!!;val job=async {model.submit(submit)};runCurrent();val pending=model.control!!;val record=model.submission!!;model.submit(submit);model.back(pending);model.acknowledge(pending,record)
        assertEquals(1,p.attempts.size);assertEquals(record,model.submission);assertTrue(model.blocked);p.pending[0].completeExceptionally(CancellationException("synthetic"));job.await();assertEquals(TaskSelfAssignmentPhase.UNKNOWN,model.submission!!.phase)
        model.bind(null);model.bind(source(revision=2));assertTrue(model.blocked);assertEquals(record.attempt,model.submission!!.attempt);assertFalse(model.canPrepare)
    }
    @Test fun lateCompletionDoesNotChangeNewOwnerAndConfirmedCannotRepeatSameRead()=runTest {
        val fixture=port();val p=Controlled(fixture.grants);val model=TaskSelfAssignmentModel(p,backgroundScope);model.bind(source());model.prepare(model.control);val sending=async {model.submit(model.control)};runCurrent()
        val foreign=TaskSelfAssignmentSource(TaskCommentRead(TaskCommentContext(202,1201,132),1),detail(202,1201).task);model.bind(foreign);val control=model.control;p.pending[0].complete(fixture.execute(p.attempts[0]));sending.await()
        assertEquals(control,model.control);assertNull(model.submission);assertTrue(model.canPrepare);assertEquals(1,model.retainedAttemptCount)
        model.bind(source());val record=model.submission!!;assertEquals(TaskSelfAssignmentPhase.CONFIRMED,record.phase);model.acknowledge(model.control,record);model.prepare(model.control);assertTrue(model.consumed);assertFalse(model.canPrepare);assertNull(model.review);assertEquals("open",model.source!!.task.status)
        model.bind(source(revision=2));assertTrue(model.canPrepare)
    }
    @Test fun rejectedWithoutWriteRequiresFreshExplicitReviewAndOldResultCannotAckIt()=runTest {
        val model=TaskSelfAssignmentModel(port(),backgroundScope);val foreign=TaskSelfAssignmentSource(TaskCommentRead(TaskCommentContext(202,1201,132),1),detail(202,1201).task);model.bind(foreign);model.prepare(model.control);model.submit(model.control)
        val old=model.control!!;val record=model.submission!!;assertEquals(TaskSelfAssignmentPhase.REJECTED,record.phase);model.acknowledge(old,record);assertTrue(model.canPrepare);assertNull(model.review);model.prepare(model.control);val fresh=model.control;model.acknowledge(old,record);assertEquals(fresh,model.control);assertNotEquals(old.review,model.review)
    }
    private inner class Repo:TaskReadRepository {
        var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return detail(business,id)}
    }
    @Test fun taskReadPreviewSiblingAndFakeResultPreserveGetProjectionListAndComments()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val provenance=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskSelfAssignmentTest.detail(detail.business,detail.task.id)};val model=TaskListViewModel(repo,commentSource=provenance,completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=port())
        try {model.load(101,133);runCurrent();model.open(1101);runCurrent();val complete=model.selfAssignment!!;val original=model.state.detail;val list=model.state.items;val total=model.state.total;val reads=repo.reads
            assertTrue(complete.canPrepare);complete.prepare(complete.control);val old=complete.control!!;model.openComment(complete.source!!.read);complete.submit(old);assertEquals(0,complete.retainedAttemptCount);assertNull(complete.review)
            model.comment!!.close(expected=model.comment!!.returnControl);complete.prepare(complete.control);complete.submit(complete.control);assertEquals(TaskSelfAssignmentPhase.CONFIRMED,complete.submission!!.phase);assertEquals(original,model.state.detail);assertEquals(list,model.state.items);assertEquals(total,model.state.total);assertEquals(reads,repo.reads)
            val peer=model.completion!!;model.prepareCompletion(peer.control,model.control);assertNull(peer.review);assertFalse(model.completionCurrent(model.control));complete.acknowledge(complete.control,complete.submission!!);model.prepareCompletion(peer.control,model.control);assertNull(peer.review);assertFalse(model.completionCurrent(model.control))
            model.back();assertNull(complete.source);assertEquals(1,complete.retainedAttemptCount)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun completionNeedsIndependentVerifiedFixtureOriginAndIsAbsentWithoutPort()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val model=TaskListViewModel(repo,selfAssignSubmission=port());val plain=TaskListViewModel(repo)
        try {model.load(101,134);runCurrent();model.open(1101);runCurrent();assertNull(model.selfAssignment!!.source);assertFalse(model.selfAssignment!!.canPrepare);assertNull(plain.selfAssignment)} finally {model.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class CompleteControlled(override val grants:List<SyntheticTaskCompleteGrant>):SyntheticTaskCompletePort {
        val attempts=mutableListOf<TaskCompletionAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCompleteOutcome>>()
        override suspend fun execute(attempt:TaskCompletionAttempt):SyntheticTaskCompleteOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskCompleteOutcome>().also {pending+=it}.await()}
    }
    @Test fun previewsAndSymmetricPendingUnknownReadBarriersCannotBypassThroughPeerOrCancel()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {for(assigning in listOf(false,true)) {
            val repo=Repo();val assignPort=Controlled(port().grants);val completePort=CompleteControlled(FixtureTaskCompletePort(fixture("task-complete-outcome")).grants)
            val provenance=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskSelfAssignmentTest.detail(detail.business,detail.task.id)}
            val list=TaskListViewModel(repo,commentSource=provenance,completeSubmission=completePort,selfAssignSubmission=assignPort)
            try {
                list.load(101,140);runCurrent();list.open(1101);runCurrent();val assign=list.selfAssignment!!;val complete=list.completion!!;val read=assign.source!!.read;val parent=list.control!!
                val actual=assign.source!!;assign.bind(actual.copy(read=actual.read.copy(context=actual.read.context.copy(epoch=999))));assertFalse(list.selfAssignmentCurrent(parent));assign.bind(actual)
                val oldAssign=assign.control!!;val oldComplete=complete.control!!;list.prepareSelfAssignment(oldAssign,parent);list.prepareCompletion(oldComplete,parent);assertNull(complete.review);assertNotNull(assign.review)
                assign.back(assign.control);list.prepareCompletion(complete.control,parent);assign.submit(oldAssign);assertTrue(assignPort.attempts.isEmpty());complete.back(complete.control)
                val sending=if(assigning) {list.prepareSelfAssignment(assign.control,parent);async {assign.submit(assign.control)}} else {list.prepareCompletion(complete.control,parent);async {complete.submit(complete.control)}}
                runCurrent();val peerBefore=if(assigning)complete.control else null;val assignmentBefore=if(!assigning)assign.control else null
                list.prepareSelfAssignment(assign.control,parent);list.prepareCompletion(complete.control,parent);list.openCancelReason(read);assertNull(list.cancelReason!!.control)
                if(assigning) {assertNull(complete.review);assertEquals(peerBefore,complete.control);assertEquals(1,assignPort.attempts.size);assignPort.pending[0].complete(SyntheticTaskSelfAssignOutcome.Unknown)}
                else {assertNull(assign.review);assertEquals(assignmentBefore,assign.control);assertEquals(1,completePort.attempts.size);completePort.pending[0].complete(SyntheticTaskCompleteOutcome.Unknown)}
                sending.await();list.back();list.load(101,141);runCurrent();list.open(1101);runCurrent();assertTrue(list.taskActionOccupied);assertFalse(if(assigning)list.completionCurrent(list.control) else list.selfAssignmentCurrent(list.control));assertEquals(1,if(assigning)assign.retainedAttemptCount else complete.retainedAttemptCount)
            } finally {list.viewModelScope.cancel()}
        }} finally {Dispatchers.resetMain()}
    }

    @Test fun cancellationUnknownAndConfirmedReadCannotBeBypassedThroughNewActions()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {for(unknownCancel in listOf(false,true)) {
            val repo=Repo();val provenance=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==this@TaskSelfAssignmentTest.detail(detail.business,detail.task.id)}
            val list=TaskListViewModel(repo,commentSource=provenance,cancelSubmission=FixtureTaskCancelPort(fixture("task-cancel-outcome")),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=port())
            try {
                list.load(101,150);runCurrent();list.open(if(unknownCancel)1102 else 1101);runCurrent();val reason=list.cancelReason!!;val read=reason.state.read!!
                list.openCancelReason(read);reason.update("Manual source reason",reason.inputControl);reason.prepare(reason.control);reason.submit(reason.state.review!!,reason.control);val record=reason.submission!!;reason.close(expected=reason.returnControl)
                list.prepareCompletion(list.completion!!.control,list.control);list.prepareSelfAssignment(list.selfAssignment!!.control,list.control);assertNull(list.completion!!.review);assertNull(list.selfAssignment!!.review)
                list.openCancelReason(read);reason.acknowledge(reason.control,record);if(unknownCancel)assertTrue(reason.submissionBlocked) else assertTrue(reason.currentReadConfirmed)
                list.retryDetail(list.detailSelection);runCurrent();assertEquals(!unknownCancel,list.selfAssignmentCurrent(list.control))
            } finally {list.viewModelScope.cancel()}
        }} finally {Dispatchers.resetMain()}
    }

}
