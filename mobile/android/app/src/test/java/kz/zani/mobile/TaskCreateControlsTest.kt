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
class TaskCreateControlsTest {
    private val context=TaskDraftContext(101,100)
    private class Port(create:Boolean=true,private val immediate:Boolean=false):SyntheticTaskCreatePort {
        override val grants=listOf(SyntheticTaskCreateGrant(101,9001,create),SyntheticTaskCreateGrant(202,9002,create))
        val attempts=mutableListOf<TaskCreateAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticTaskCreateOutcome>>()
        override suspend fun execute(attempt:TaskCreateAttempt):SyntheticTaskCreateOutcome {attempts+=attempt;if(immediate)return SyntheticTaskCreateOutcome.RejectedWithoutWrite;return CompletableDeferred<SyntheticTaskCreateOutcome>().also {pending+=it}.await()}
    }
    private fun model(port:Port?=null,scope:CoroutineScope?=null)=TaskDraftModel(port,scope).also {it.bind(context)}
    private fun values(m:TaskDraftModel) {val input=m.inputControl;m.update(TaskDraftField.TITLE,"  Manual title  \n",input);m.update(TaskDraftField.DESCRIPTION,"  Description  \n",input);m.update(TaskDraftField.PRIORITY,"high",input)}
    private fun response(a:TaskCreateAttempt):SyntheticTaskCreateOutcome {val v=a.review.preview;return SyntheticTaskCreateOutcome.Response(201,WorkTask(88001,v.title,"open",v.priority,null,business=a.authorization.context.business,updatedAt="2026-10-30T12:00:00Z",description=v.description,createdBy=a.authorization.actor,createdAt="2026-10-30T12:00:00Z"))}
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun entryFieldsValidationAndSameContextBindPreserveContinuousRawValues() {
        val m=TaskDraftModel();m.open(null as TaskDraftEntryControl?);assertNull(m.control);m.bind(context);val entry=m.entryControl!!;m.open(entry);val control=m.control!!;val input=m.inputControl!!
        m.open(entry);m.prepare(control);assertEquals(control,m.control);assertTrue(m.state.issues.any {it.problem==TaskDraftProblem.REQUIRED})
        m.update(TaskDraftField.TITLE,"x".repeat(256),input);m.update(TaskDraftField.DESCRIPTION,"ab\u0000cd",input);m.update(TaskDraftField.PRIORITY,"unsupported",input);m.prepare(control)
        assertEquals(TaskDraftField.entries.filterNot {it==TaskDraftField.DUE_AT || it==TaskDraftField.REMINDER_AT}.toSet(),m.state.issues.map {it.field}.toSet());assertEquals(TaskDraftDueMode.OMIT,m.state.values.dueDate.mode);assertEquals(input,m.inputControl);values(m);val raw=m.state.values;m.bind(context)
        assertEquals(raw,m.state.values);assertEquals(input,m.inputControl);m.prepare(control);assertEquals(raw,m.state.review!!.values);assertEquals("Manual title",m.state.review!!.preview.title);assertEquals("Description",m.state.review!!.preview.description)
    }
    @Test fun identicalReviewRoundtripRejectsOldSubmitBackAndPriorityEvent()=runTest {
        val port=Port(immediate=true);val m=model(port);m.open(m.entryControl);values(m);val edit=m.control!!;val input=m.inputControl!!;m.prepare(edit);val old=m.control!!;val review=m.state.review!!
        m.back(expected=m.returnControl);m.prepare(m.control);val current=m.control;m.submit(review,old);m.back(expected=TaskDraftReturnControl(edit,null));m.update(TaskDraftField.PRIORITY,"urgent",input)
        assertEquals(review,m.state.review);assertNotEquals(old,current);assertEquals(current,m.control);assertTrue(port.attempts.isEmpty());assertEquals("high",m.state.values.priority)
    }
    @Test fun clearConsentRejectsNewFieldEditReplacementAndClosedReopenedComposer() {
        val m=model();val entry=m.entryControl!!;m.open(entry);values(m);val control=m.control!!;val input=m.inputControl!!;m.askClear(control);val question=m.clearConfirmation!!
        m.update(TaskDraftField.DESCRIPTION,"Own newer description",input);m.confirmClear(question);assertNull(m.clearConfirmation);assertEquals("Own newer description",m.state.values.description)
        m.askClear(control);val old=m.clearConfirmation!!;m.dismissClear(old);m.askClear(control);val current=m.clearConfirmation!!;m.dismissClear(old);m.confirmClear(old);m.back(expected=TaskDraftReturnControl(control,null));assertEquals(current,m.clearConfirmation)
        m.back(expected=m.returnControl);m.close(expected=m.returnControl);m.open(entry);assertNull(m.control);m.open(m.entryControl);m.confirmClear(current);assertEquals("Own newer description",m.state.values.description)
        m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);assertNull(m.control);assertEquals(TaskDraftValues(),m.state.values)
    }
    @Test fun pendingAttemptRevokesClearFieldEventsAndQueuedDuplicatesWhileBackRetainsIt()=runTest {
        val port=Port();val m=model(port,backgroundScope);m.open(m.entryControl);values(m);m.prepare(m.control);val control=m.control!!;val review=m.state.review!!;m.askClear(control);val consent=m.clearConfirmation!!
        val job=backgroundScope.launch {m.submit(review)};runCurrent();val record=m.submission!!;m.confirmClear(consent);m.askClear(m.control);m.update(TaskDraftField.TITLE,"overwrite",TaskDraftInputControl(control));m.launchSubmit(review,control);runCurrent()
        assertNull(m.clearConfirmation);assertNull(m.inputControl);assertEquals(record,m.submission);assertEquals(review.values,m.state.values);assertEquals(1,port.attempts.size)
        m.back(expected=m.returnControl);assertNull(m.control);assertEquals(record,m.submission);m.open(m.entryControl);port.pending[0].complete(SyntheticTaskCreateOutcome.Unknown);runCurrent();job.join();assertEquals(TaskCreateAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked)
    }
    @Test fun rejectedAcknowledgementRequiresCurrentTerminalVisitAndFreshReview()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);values(m);m.prepare(m.control);val review=m.state.review!!;val old=m.control!!;val job=launch {m.submit(review,old)};runCurrent();val pending=m.control!!
        m.back(expected=m.returnControl);m.open(m.entryControl);val reopened=m.control!!;port.pending[0].complete(SyntheticTaskCreateOutcome.RejectedWithoutWrite);job.join();val result=m.submission!!;val current=m.control!!
        m.acknowledge(pending,result);m.acknowledge(reopened,result);assertEquals(result,m.submission);m.acknowledge(current,result)
        assertFalse(m.submissionBlocked);assertEquals(review.values,m.state.values);assertEquals(TaskDraftPhase.EDITING,m.state.phase);assertEquals(1,m.retainedAttemptCount);m.submit(review,old);assertEquals(1,port.attempts.size)
        m.prepare(m.control);val second=launch {m.submit(m.state.review!!,m.control)};runCurrent();assertEquals(2,port.attempts.size);port.pending[1].complete(SyntheticTaskCreateOutcome.Unknown);second.join()
    }
    @Test fun unknownMatchingBindingAndNewEpochCannotResolveOrReplayBusinessAttempt()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);values(m);m.prepare(m.control);val review=m.state.review!!;val control=m.control!!;val job=launch {m.submit(review,control)};runCurrent();port.pending[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));job.join()
        val unknown=m.submission!!;val current=m.control!!;m.bind(context);m.askClear(current);m.discard(current.selection);m.acknowledge(current,unknown);m.submit(review,current)
        assertEquals(unknown,m.submission);assertTrue(m.submissionBlocked);assertEquals(review.values,m.state.values);assertNull(m.clearConfirmation);assertEquals(1,port.attempts.size)
        m.bind(context.copy(epoch=101));m.open(m.entryControl);assertNull(m.submission);assertTrue(m.submissionBlocked);assertNull(m.inputControl);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun lateOtherBusinessCompletionAndMissingGrantOrCancellationNeverFabricateSuccess()=runTest {
        for(port in listOf(null,Port(false))) {val m=model(port);m.open(m.entryControl);values(m);m.prepare(m.control);m.submit(m.state.review!!,m.control);assertFalse(m.canSubmit);assertEquals(0,m.retainedAttemptCount)}
        val port=Port();val m=model(port);m.open(m.entryControl);values(m);m.prepare(m.control);val job=launch {m.submit(m.state.review!!,m.control)};runCurrent()
        m.bind(TaskDraftContext(202,102));m.open(m.entryControl);val input=m.inputControl!!;val control=m.control;m.update(TaskDraftField.TITLE,"Other Business raw",input);port.pending[0].complete(SyntheticTaskCreateOutcome.Unknown);job.join()
        assertEquals(input,m.inputControl);assertEquals(control,m.control);assertEquals("Other Business raw",m.state.values.title);assertFalse(m.submissionBlocked);assertEquals(1,m.retainedAttemptCount)
        values(m);m.prepare(m.control);val canceled=launch {m.submit(m.state.review!!,m.control)};runCurrent();canceled.cancelAndJoin();assertEquals(TaskCreateAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked)
    }
    @Test fun fixtureListEntryBlocksHiddenControlsAndConfirmedResultNeverMutatesSourceRows()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val port=Port();val calls=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->calls+=r;ReadResponse(200,fixture(if(r.path.endsWith("/1101/"))"task-101-1101" else "tasks-101"))});val parent=TaskListViewModel(repo,createSubmission=port)
        try {
            parent.load(101,100);runCurrent();val list=parent.control!!;val query=parent.querySelection;val rows=parent.state.items;val total=parent.state.total;val before=calls.toList();val m=parent.draft;val opening=m.entryControl!!
            parent.openDraft(opening,list);values(m);val control=m.control!!;val activeList=parent.control!!;parent.search("hidden",list);parent.filterStatus("done",null,list);parent.applyFilter(TaskQueryFilter("done",TaskDueFilter.TODAY),query);parent.refreshFilter(query);parent.retryList(list);parent.open(1101,list);runCurrent()
            assertEquals(activeList,parent.control);assertNotEquals(list,activeList);assertNull(parent.state.selectedID);assertEquals("",parent.state.query);assertEquals(TaskQueryFilter(),parent.state.appliedFilter);assertEquals(control,m.control);assertEquals(before,calls)
            m.prepare(m.control);val sending=m.control!!;val job=launch {m.submit(m.state.review!!,sending)};runCurrent();port.pending[0].complete(response(port.attempts[0]));job.join();val result=m.submission!!
            m.acknowledge(sending,result);assertTrue(m.submissionBlocked);m.acknowledge(m.control,result);assertNull(m.control);assertEquals(TaskDraftValues(),m.state.values);assertEquals(1,m.retainedAttemptCount)
            assertEquals(rows,parent.state.items);assertEquals(total,parent.state.total);assertEquals("",parent.state.query);assertEquals(before,calls);parent.openDraft(opening,list);assertNull(m.control)
            parent.open(1101,list);runCurrent();assertNull(parent.state.selectedID);parent.open(1101,parent.control);runCurrent();val detail=parent.detailSelection;parent.openDraft(m.entryControl,activeList);assertEquals(detail,parent.detailSelection);assertEquals(1101,parent.state.selectedID);assertNull(m.control)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
