package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskCommentControlsTest {
    private val context=TaskCommentContext(101,1101,90)
    private val read=TaskCommentRead(context,1)
    private class Port(update:Boolean=true):SyntheticTaskCommentPort {
        override val grants=listOf(SyntheticTaskCommentGrant(101,1101,9001,update))
        val attempts=mutableListOf<TaskCommentAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCommentOutcome>>()
        override suspend fun execute(attempt:TaskCommentAttempt):SyntheticTaskCommentOutcome {attempts+=attempt;return CompletableDeferred<SyntheticTaskCommentOutcome>().also {pending+=it}.await()}
    }
    private fun model(port:Port?=null,scope:CoroutineScope?=null)=TaskCommentModel(port,scope).also {it.begin(read);it.receive(true,read)}
    private fun response(attempt:TaskCommentAttempt)=SyntheticTaskCommentOutcome.Response(201,TaskComment(8801,attempt.text,"2026-10-30T12:00:00Z",1101,9001,"Synthetic employee","fixture@example.invalid"))
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun entryContinuousInputEmptyValidationAndSameTextReviewRejectOldSubmitVisit()=runTest {
        val port=Port();val m=TaskCommentModel(port);m.open(null as TaskCommentEntryControl?);assertNull(m.control);m.begin(read);assertNull(m.entryControl)
        m.receive(true,read);val entry=m.entryControl!!;m.open(entry);val control=m.control!!;val input=m.inputControl!!;m.open(entry);m.prepare(control)
        assertEquals(control,m.control);assertTrue(m.state.emptyError);m.update("  Same raw text  \n",input);assertEquals(input,m.inputControl);m.prepare(control)
        val review=m.state.review!!;val old=m.control!!;m.back(expected=m.returnControl);m.prepare(m.control)
        assertEquals(review,m.state.review);assertNotEquals(old,m.control);m.update("old typing",input);m.back(expected=TaskCommentReturnControl(control,null));m.submit(review,old)
        assertTrue(port.attempts.isEmpty());assertEquals("Same raw text",m.state.review!!.text);assertEquals("  Same raw text  \n",m.state.text)
    }
    @Test fun exactClearConsentRejectsNewInputReplacementAndClosedReopenedEditor()=runTest {
        val m=model();m.open(m.entryControl);val control=m.control!!;val input=m.inputControl!!;m.update("Own original",input);m.askClear(control);val old=m.clearConfirmation!!
        m.update("Own new text",input);m.confirmClear(old);assertNull(m.clearConfirmation);assertEquals("Own new text",m.state.text)
        m.askClear(control);val dismissed=m.clearConfirmation!!;m.dismissClear(dismissed);m.askClear(control);val current=m.clearConfirmation!!;m.dismissClear(dismissed);m.confirmClear(dismissed)
        assertEquals(current,m.clearConfirmation);m.back(expected=TaskCommentReturnControl(control,null));assertEquals(current,m.clearConfirmation)
        m.back(expected=m.returnControl);assertNull(m.clearConfirmation);assertEquals(control,m.control);m.close(expected=m.returnControl);m.open(m.entryControl);m.confirmClear(current)
        assertEquals("Own new text",m.state.text);m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);assertNull(m.control);assertEquals("",m.state.text)
    }
    @Test fun pendingSubmitRevokesOldClearAndQueuedDuplicateWithoutLosingAttemptOnBack()=runTest {
        val port=Port();val m=model(port,backgroundScope);m.open(m.entryControl);m.update("  Immutable raw  \n",m.inputControl);m.prepare(m.control)
        val control=m.control!!;val review=m.state.review!!;m.askClear(control);val consent=m.clearConfirmation!!
        val job=backgroundScope.launch {m.submit(review)};runCurrent();val record=m.submission!!;val pending=m.control!!
        m.confirmClear(consent);m.askClear(pending);m.update("overwrite",TaskCommentInputControl(control));m.launchSubmit(review,control);runCurrent()
        assertNull(m.clearConfirmation);assertNull(m.inputControl);assertEquals(record,m.submission);assertEquals("  Immutable raw  \n",m.state.text);assertEquals(1,port.attempts.size)
        m.back(expected=m.returnControl);assertNull(m.control);assertEquals(record,m.submission);m.open(m.entryControl);assertTrue(m.submissionBlocked)
        port.pending[0].complete(SyntheticTaskCommentOutcome.Unknown);runCurrent();job.join();assertEquals(TaskCommentAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked)
    }
    @Test fun rejectedAcknowledgementRequiresCurrentResultVisitAndFreshExplicitReview()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);m.update("  Preserve raw input  ",m.inputControl);m.prepare(m.control)
        val review=m.state.review!!;val old=m.control!!;val job=launch {m.submit(review,old)};runCurrent();val pending=m.control!!;m.back(expected=m.returnControl);m.open(m.entryControl);val reopened=m.control!!
        port.pending[0].complete(SyntheticTaskCommentOutcome.RejectedWithoutWrite);job.join();val result=m.submission!!;val current=m.control!!
        m.acknowledge(pending,result);m.acknowledge(reopened,result);assertEquals(result,m.submission);assertNotEquals(reopened,current)
        m.acknowledge(current,result);assertFalse(m.submissionBlocked);assertEquals(TaskCommentPhase.EDITING,m.state.phase);assertEquals("  Preserve raw input  ",m.state.text);assertEquals(1,m.retainedAttemptCount)
        m.submit(review,old);assertEquals(1,port.attempts.size);m.prepare(m.control);val second=launch {m.submit(m.state.review!!,m.control)};runCurrent();assertEquals(2,port.attempts.size)
        port.pending[1].complete(SyntheticTaskCommentOutcome.Unknown);second.join();assertEquals(TaskCommentAttemptPhase.UNKNOWN,m.submission!!.phase)
    }
    @Test fun unknownSurvivesMatchingReadEpochChangeAndAllOldConsentWithoutReplay()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);m.update("  Uncertain own text  ",m.inputControl);m.prepare(m.control);val control=m.control!!;val review=m.state.review!!
        val job=launch {m.submit(review,control)};runCurrent();port.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));job.join();val unknown=m.submission!!
        val reread=read.copy(revision=2);m.begin(reread);m.receive(true,reread);m.open(m.entryControl);val current=m.control!!
        m.askClear(current);m.discard(current.selection);m.acknowledge(current,unknown);m.submit(review,current)
        assertEquals(unknown,m.submission);assertTrue(m.submissionBlocked);assertNull(m.clearConfirmation);assertNull(m.inputControl);assertEquals(unknown.attempt.raw,m.state.text);assertEquals(1,port.attempts.size)
        val epoch=reread.copy(context=context.copy(epoch=91),revision=3);m.begin(epoch);m.receive(true,epoch);m.open(m.entryControl);m.acknowledge(current,unknown)
        assertNull(m.submission);assertTrue(m.submissionBlocked);assertNull(m.inputControl);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun lateForeignCompletionAndOldReadDoNotRevokeCurrentOtherTaskInput()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);m.update("Old Task raw",m.inputControl);m.prepare(m.control);val old=m.control!!;val review=m.state.review!!
        val job=launch {m.submit(review,old)};runCurrent();val other=read.copy(context=context.copy(task=1102),revision=2);m.begin(other);m.receive(true,other);m.open(m.entryControl)
        val input=m.inputControl!!;val control=m.control;m.update("Other Task own text",input);m.receive(true,read);port.pending[0].complete(SyntheticTaskCommentOutcome.Unknown);job.join()
        assertEquals(control,m.control);assertEquals(input,m.inputControl);assertEquals("Other Task own text",m.state.text);assertFalse(m.submissionBlocked);assertEquals(1,m.retainedAttemptCount);assertFalse(m.canSubmit)
    }
    @Test fun exactConfirmedResultAndParentChildBackPreserveTaskProjectionAndReadCounts()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val port=Port();val calls=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->calls+=r;ReadResponse(200,fixture(if(r.path.endsWith("/1101/"))"task-101-1101" else "tasks-101"))})
        val source=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=detail==JsonContracts.taskDetails(fixture("task-101-1101"))}
        val parent=TaskListViewModel(repo,source,port)
        try {
            parent.load(101,90);runCurrent();parent.open(1101);runCurrent();val m=parent.comment!!;val detail=parent.state.detail;val rows=parent.state.items;val before=calls.toList();val parentBack=parent.detailReturnControl
            parent.openComment(m.state.read!!);val editing=parent.detailReturnControl;m.update("  Parent comment  ",m.inputControl);m.prepare(m.control);val review=parent.detailReturnControl
            assertEquals(TaskChildBack.STALE,parent.backChildren(parentBack));assertEquals(TaskChildBack.STALE,parent.backChildren(editing));assertEquals(1101,parent.state.selectedID)
            assertEquals(TaskChildBack.CLOSED,parent.backChildren(review));m.prepare(m.control);assertEquals(TaskChildBack.STALE,parent.backChildren(review))
            val sending=m.control!!;val job=launch {m.submit(m.state.review!!,sending)};runCurrent();val pending=parent.detailReturnControl
            port.pending[0].complete(response(port.attempts[0]));job.join();val result=m.submission!!;val current=m.control!!
            assertEquals(TaskChildBack.STALE,parent.backChildren(pending));m.acknowledge(sending,result);assertTrue(m.submissionBlocked);m.acknowledge(current,result)
            assertFalse(m.submissionBlocked);assertNull(m.control);assertEquals("",m.state.text);assertEquals(1,m.retainedAttemptCount);assertEquals(TaskChildBack.NO_CHILD,parent.backChildren(parent.detailReturnControl))
            assertEquals(detail,parent.state.detail);assertEquals(rows,parent.state.items);assertEquals(before,calls)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun readabilityWithoutUpdateNeverCreatesAttemptAndCancellationStaysUnknown()=runTest {
        for(port in listOf(null,Port(false))) {
            val m=model(port);m.open(m.entryControl);m.update("Readable only",m.inputControl);m.prepare(m.control);m.submit(m.state.review!!,m.control)
            assertFalse(m.canSubmit);assertEquals(0,m.retainedAttemptCount)
        }
        val port=Port();val m=model(port);m.open(m.entryControl);m.update("Canceled fake reply",m.inputControl);m.prepare(m.control)
        val job=launch {m.submit(m.state.review!!,m.control)};runCurrent();job.cancelAndJoin()
        assertEquals(TaskCommentAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked);assertEquals("Canceled fake reply",m.state.text);assertEquals(1,port.attempts.size)
    }
}
