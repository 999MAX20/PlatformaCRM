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
class TaskWatcherTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(b:Int=101,id:Int=1101)=JsonContracts.taskDetails(fixture("task-$b-$id"))
    private fun source(payload:TaskDetails=detail(),epoch:Int=190,revision:Int=1)=TaskWatcherSource(TaskCommentRead(TaskCommentContext(payload.business,payload.task.id,epoch),revision),payload.task)
    private fun port()=FixtureTaskWatcherPort(fixture("task-watcher-outcome"))
    private val context=TaskCommentContext(101,1101,190)
    private class Controlled(override val grants:List<SyntheticTaskWatcherGrant>):SyntheticTaskWatcherPort {val attempts=mutableListOf<TaskWatcherAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskWatcherOutcome>>()
        override suspend fun execute(attempt:TaskWatcherAttempt):SyntheticTaskWatcherOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskWatcherOutcome>().also {pending+=it}.await()}
    }
    @Test fun sourceEligibilityAndSeparateUpdateMemberGrantNeverComeFromGet()=runTest {
        assertNull(SyntheticTaskWatcherGrant(101,1101,9001,false,true).authorization(context));assertNull(SyntheticTaskWatcherGrant(101,1101,9001,true,false).authorization(context));assertNull(SyntheticTaskWatcherGrant(202,1101,9001,true,true).authorization(context));assertNull(SyntheticTaskWatcherGrant(101,1101,0,true,true).authorization(context))
        for(status in listOf("done","cancelled","waiting","")) {val s=source().copy(task=detail().task.copy(status=status));assertTrue(s.identityValid);assertFalse(s.valid);assertNull(TaskWatcherLedger().begin(TaskWatcherReview(s,1),port().grants[0].authorization(context)!!))};assertTrue(source().copy(task=detail().task.copy(status="in_progress")).valid)
    }
    @Test fun shared33CasesValidateMembershipNotCountAndKeepSourceStatus()=runTest {
        val cases=JSONObject(fixture("task-watcher-outcome")).getJSONArray("validation_cases");assertEquals(33,cases.length())
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val s=source().copy(task=detail().task.copy(status=row.optString("source_status","open")));val l=TaskWatcherLedger();val a=port().grants[0].authorization(context)!!;val review=TaskWatcherReview(s,1);val attempt=l.begin(review,a)!!;assertNull(l.begin(review,a))
            l.complete(attempt,SyntheticTaskWatcherOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=l.visible(a)!!;assertEquals(row.getString("name"),if(row.getString("expected")=="confirmed")TaskWatcherPhase.CONFIRMED else TaskWatcherPhase.UNKNOWN,record.phase)
            l.complete(attempt,SyntheticTaskWatcherOutcome.RejectedWithoutWrite);assertEquals(record,l.visible(a));assertEquals(s,record.attempt.review.source);if(record.phase==TaskWatcherPhase.UNKNOWN)assertFalse(l.acknowledge(a));record.result?.let {assertEquals(s.task.status,it.status);assertTrue(a.actor in it.watchers)}
        }
    }
    @Test fun stringFlagsAndActorCannotBecomeFixtureMembershipAuthority()=runTest {
        for(key in listOf("active_member","update","actor")) {val raw=JSONObject(fixture("task-watcher-outcome"));raw.getJSONArray("scenarios").getJSONObject(0).getJSONObject("grant").put(key,if(key=="actor")"9001" else "true");assertTrue(FixtureTaskWatcherPort(raw.toString()).grants.isEmpty())}
        val raw=JSONObject(fixture("task-watcher-outcome")).put("fixture_only","true");assertTrue(FixtureTaskWatcherPort(raw.toString()).grants.isEmpty())
    }
    @Test fun staleIdenticalReviewAndPendingBackAckCannotRepeatWatch()=runTest {
        val p=Controlled(port().grants);val m=TaskWatcherModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val stale=m.control;m.back(stale);m.prepare(m.control);m.submit(stale);assertTrue(p.attempts.isEmpty());val submit=m.control;val job=async {m.submit(submit)};runCurrent();val pending=m.control;val record=m.submission!!;m.submit(pending);m.back(pending);m.acknowledge(pending,record);assertEquals(1,p.attempts.size);assertEquals(record,m.submission);p.pending[0].complete(SyntheticTaskWatcherOutcome.Unknown);job.await()
    }
    @Test fun matchingReadTerminalStatusAndNewEpochCannotProveUnknown()=runTest {
        val p=Controlled(port().grants);val m=TaskWatcherModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();p.pending[0].complete(SyntheticTaskWatcherOutcome.Unknown);job.await();val attempt=m.submission!!.attempt
        m.bind(source(revision=2));assertTrue(m.blocked);assertEquals(attempt,m.submission!!.attempt);m.bind(source().copy(read=TaskCommentRead(context.copy(epoch=191),3),task=detail().task.copy(status="done")));assertNull(m.submission);assertTrue(m.blocks(context));assertTrue(m.canPresent);assertFalse(m.canPrepare);m.bind(null);assertEquals(1,m.retainedAttemptCount);assertTrue(m.blocks(context))
    }
    @Test fun lateForeignOutcomeDoesNotMutateReplacementAndConfirmedReadIsConsumed()=runTest {
        val fixture=port();val p=Controlled(fixture.grants);val m=TaskWatcherModel(p,backgroundScope);m.bind(source());m.prepare(m.control);val job=async {m.submit(m.control)};runCurrent();m.bind(source(detail(202,1201),192));val replacement=m.control;p.pending[0].complete(fixture.execute(p.attempts[0]));job.await();assertEquals(replacement,m.control);assertNull(m.submission);assertTrue(m.canPrepare)
        m.bind(source());val result=m.submission!!;assertEquals(TaskWatcherPhase.CONFIRMED,result.phase);assertEquals("open",result.result!!.status);m.acknowledge(m.control,result);m.prepare(m.control);assertTrue(m.consumed);assertNull(m.review);m.bind(source(revision=2));assertTrue(m.canPrepare)
    }
    @Test fun noWriteAndThrownOutcomeRetainExplicitReviewAndOriginalAttempt()=runTest {
        val m=TaskWatcherModel(port(),backgroundScope);m.bind(source(detail(101,1401)));m.prepare(m.control);m.submit(m.control);val record=m.submission!!;m.acknowledge(m.control,record);assertEquals(TaskWatcherPhase.REJECTED,record.phase);assertTrue(m.canPrepare);assertNull(m.review)
        val p=Controlled(port().grants);val held=TaskWatcherModel(p,backgroundScope);val original=source();held.bind(original);held.prepare(held.control);val job=async {held.submit(held.control)};runCurrent();p.pending[0].completeExceptionally(CancellationException("synthetic"));job.await();assertEquals(TaskWatcherPhase.UNKNOWN,held.submission!!.phase);assertEquals(original,held.submission!!.attempt.review.source)
    }
    private inner class Repo:TaskReadRepository {var selected=detail();var reads=0
        override suspend fun tasks(business:Int):TaskPage {reads++;return JsonContracts.tasks(fixture("tasks-$business"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {reads++;return if(selected.business==business && selected.task.id==id)selected else detail(business,id)}
    }
    private fun origin(allowed:List<TaskDetails>)=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail in allowed}
    @Test fun defaultAndGetOnlyCompositionHaveNoWatcherAuthority()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val plain=TaskListViewModel(repo);val m=TaskListViewModel(repo,watcherSubmission=port())
        try {m.load(101,193);runCurrent();m.open(1101);runCurrent();assertNull(plain.watcherAction);assertNull(m.watcherAction!!.source)} finally {m.viewModelScope.cancel();plain.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun currentTaskMetadataAndConfirmedWatchPreserveSourceAndConsumePeerRead()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),cancelSubmission=FixtureTaskCancelPort(fixture("task-cancel-outcome")),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),reopenSubmission=FixtureTaskReopenPort(fixture("task-reopen-outcome")),fileMetadataPort=FixtureTaskFileMetadataPort(fixture("task-file-metadata")),watcherSubmission=port())
        try {m.load(101,194);runCurrent();m.open(1101);runCurrent();val watch=m.watcherAction!!;val before=m.state.detail;val items=m.state.items;val reads=repo.reads;m.prepareWatcher(watch.control,m.control);val stale=watch.control;m.openComment(watch.source!!.read);watch.submit(stale);assertEquals(0,watch.retainedAttemptCount);m.comment!!.close(expected=m.comment!!.returnControl)
            m.prepareWatcher(watch.control,m.control);watch.submit(watch.control);val record=watch.submission!!;assertEquals(TaskWatcherPhase.CONFIRMED,record.phase);assertEquals(before,m.state.detail);assertEquals(items,m.state.items);assertEquals(reads,repo.reads)
            val files=m.fileMetadata!!;files.load(files.control);files.select(files.items[0],files.control);files.back(files.control);assertEquals(record,watch.submission);assertEquals(before,m.state.detail)
            watch.acknowledge(watch.control,record);m.prepareCompletion(m.completion!!.control,m.control);m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);m.prepareStart(m.startAction!!.control,m.control);m.openCancelReason(watch.source!!.read);assertNull(m.completion!!.review);assertNull(m.selfAssignment!!.review);assertNull(m.startAction!!.review);assertNull(m.cancelReason!!.control)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun retainedWatchBlocksEveryPeerAcrossEligibleAndIneligibleRereads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val original=detail();val progress=original.copy(task=original.task.copy(status="in_progress"));val done=original.copy(task=original.task.copy(status="done"));val repo=Repo();val p=Controlled(port().grants)
        val reopen=object:SyntheticTaskReopenPort {override val grants=listOf(SyntheticTaskReopenGrant(101,1101,9001,true));override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}
        val m=TaskListViewModel(repo,commentSource=origin(listOf(original,progress,done,detail(202,1201))),completeSubmission=FixtureTaskCompletePort(fixture("task-complete-outcome")),selfAssignSubmission=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")),startSubmission=FixtureTaskStartPort(fixture("task-start-outcome")),reopenSubmission=reopen,watcherSubmission=p)
        try {m.load(101,195);runCurrent();m.open(1101);runCurrent();val w=m.watcherAction!!;m.prepareWatcher(w.control,m.control);val job=async {w.submit(w.control)};runCurrent();p.pending[0].complete(SyntheticTaskWatcherOutcome.Unknown);job.await();repo.selected=progress;m.retryDetail(m.detailSelection);runCurrent();m.prepareCompletion(m.completion!!.control,m.control);m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);assertNull(m.completion!!.review);assertNull(m.selfAssignment!!.review)
            repo.selected=original;m.retryDetail(m.detailSelection);runCurrent();m.prepareStart(m.startAction!!.control,m.control);assertNull(m.startAction!!.review);repo.selected=done;m.retryDetail(m.detailSelection);runCurrent();m.prepareReopen(m.reopenAction!!.control,m.control);assertTrue(m.reopenAction!!.canPrepare);assertNull(m.reopenAction!!.review);assertEquals(TaskWatcherPhase.UNKNOWN,w.submission!!.phase);m.load(202,196);runCurrent();m.open(1201);runCurrent();assertFalse(m.taskActionOccupied);assertTrue(w.canPrepare);assertEquals(1,w.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun everyOldActionUnknownAlsoBlocksNewlyEligibleWatcher()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {for(kind in 0..3) {val initial=detail(101,if(kind==3)1103 else 1101);val open=initial.copy(task=initial.task.copy(status="open"));val repo=Repo().also {it.selected=initial}
            val c=object:SyntheticTaskCompletePort {override val grants=FixtureTaskCompletePort(fixture("task-complete-outcome")).grants;override suspend fun execute(attempt:TaskCompletionAttempt)=SyntheticTaskCompleteOutcome.Unknown}
            val a=object:SyntheticTaskSelfAssignPort {override val grants=FixtureTaskSelfAssignPort(fixture("task-self-assign-outcome")).grants;override suspend fun execute(attempt:TaskSelfAssignmentAttempt)=SyntheticTaskSelfAssignOutcome.Unknown}
            val s=object:SyntheticTaskStartPort {override val grants=FixtureTaskStartPort(fixture("task-start-outcome")).grants;override suspend fun execute(attempt:TaskStartAttempt)=SyntheticTaskStartOutcome.Unknown}
            val r=object:SyntheticTaskReopenPort {override val grants=FixtureTaskReopenPort(fixture("task-reopen-outcome")).grants;override suspend fun execute(attempt:TaskReopenAttempt)=SyntheticTaskReopenOutcome.Unknown}
            val w=Controlled(listOf(SyntheticTaskWatcherGrant(101,initial.task.id,9001,true,true)));val m=TaskListViewModel(repo,commentSource=origin(listOf(initial,open)),completeSubmission=c,selfAssignSubmission=a,startSubmission=s,reopenSubmission=r,watcherSubmission=w)
            try {m.load(101,197);runCurrent();m.open(initial.task.id);runCurrent();when(kind) {0->{m.prepareCompletion(m.completion!!.control,m.control);m.completion!!.submit(m.completion!!.control)};1->{m.prepareSelfAssignment(m.selfAssignment!!.control,m.control);m.selfAssignment!!.submit(m.selfAssignment!!.control)};2->{m.prepareStart(m.startAction!!.control,m.control);m.startAction!!.submit(m.startAction!!.control)};else->{m.prepareReopen(m.reopenAction!!.control,m.control);m.reopenAction!!.submit(m.reopenAction!!.control)}}
                repo.selected=open;m.retryDetail(m.detailSelection);runCurrent();m.prepareWatcher(m.watcherAction!!.control,m.control);assertTrue(m.watcherAction!!.canPrepare);assertNull(m.watcherAction!!.review);assertTrue(m.taskActionOccupied);assertEquals(0,m.watcherAction!!.retainedAttemptCount)
            } finally {m.viewModelScope.cancel()}
        }} finally {Dispatchers.resetMain()}
    }
    @Test fun retainedCancellationCannotBeBypassedThroughWatcher()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val cancel=object:SyntheticTaskCancelPort {override val grants=FixtureTaskCancelPort(fixture("task-cancel-outcome")).grants;override suspend fun execute(attempt:TaskCancelAttempt)=SyntheticTaskCancelOutcome.Unknown};val m=TaskListViewModel(repo,commentSource=origin(listOf(detail())),cancelSubmission=cancel,watcherSubmission=port())
        try {m.load(101,198);runCurrent();m.open(1101);runCurrent();val reason=m.cancelReason!!;m.openCancelReason(reason.state.read!!);reason.update("Manual source reason",reason.inputControl);reason.prepare(reason.control);reason.submit(reason.state.review!!,reason.control);reason.close(expected=reason.returnControl);m.prepareWatcher(m.watcherAction!!.control,m.control);assertNull(m.watcherAction!!.review);assertTrue(reason.submissionBlocked)} finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
