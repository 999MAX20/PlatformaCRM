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
class ClientCreateControlsTest {
    private val context=ClientDraftContext(101,100)
    private class Port(create:Boolean=true,private val immediate:Boolean=false):SyntheticClientCreatePort {
        override val grants=listOf(SyntheticClientCreateGrant(101,9001,create),SyntheticClientCreateGrant(202,9002,create))
        val attempts=mutableListOf<ClientCreateAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticClientCreateOutcome>>()
        override suspend fun execute(attempt:ClientCreateAttempt):SyntheticClientCreateOutcome {attempts+=attempt;if(immediate)return SyntheticClientCreateOutcome.RejectedWithoutWrite;return CompletableDeferred<SyntheticClientCreateOutcome>().also {pending+=it}.await()}
    }
    private fun model(port:Port?=null,scope:CoroutineScope?=null)=ClientDraftModel(port,scope).also {it.bind(context)}
    private fun values(m:ClientDraftModel) {val input=m.inputControl;for((field,value) in listOf(ClientDraftField.FULL_NAME to "  Manual client  \n",ClientDraftField.PHONE to "  +7 123\n",ClientDraftField.EMAIL to "alpha@example.invalid",ClientDraftField.SOURCE to "telegram",ClientDraftField.NOTES to "  Notes  \n"))m.update(field,value,input)}
    private fun response(a:ClientCreateAttempt):SyntheticClientCreateOutcome {val v=a.review.preview;return SyntheticClientCreateOutcome.Response(201,ClientContact(87001,null,v.phone,v.email,a.authorization.context.business,v.fullName,v.source,v.notes,"2026-10-30T12:00:00Z","2026-10-30T12:00:00Z"))}
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun entryFieldsValidationAndSameContextBindPreserveContinuousRawValues() {
        val m=ClientDraftModel();m.open(null as ClientDraftEntryControl?);assertNull(m.control);m.bind(context);val entry=m.entryControl!!;m.open(entry);val control=m.control!!;val input=m.inputControl!!
        m.open(entry);m.prepare(control);assertEquals(control,m.control);assertTrue(m.state.issues.any {it.problem==ClientDraftProblem.NAME})
        m.update(ClientDraftField.FULL_NAME,"x".repeat(256),input);m.update(ClientDraftField.PHONE,"1".repeat(33),input);m.update(ClientDraftField.EMAIL,"bad address",input);m.update(ClientDraftField.NOTES,"ab\u0000cd",input);m.update(ClientDraftField.SOURCE,"unsupported",input);m.prepare(control)
        assertEquals(ClientDraftField.entries.toSet(),m.state.issues.map {it.field}.toSet());assertEquals(input,m.inputControl);values(m);m.update(ClientDraftField.EMAIL," alpha@example.invalid ",input);m.prepare(control);assertEquals(control,m.control);assertTrue(m.state.issues.any {it.field==ClientDraftField.EMAIL});m.update(ClientDraftField.EMAIL,"alpha@example.invalid",input);val raw=m.state.values;m.bind(context)
        assertEquals(raw,m.state.values);assertEquals(input,m.inputControl);m.prepare(control);assertEquals(raw,m.state.review!!.values);assertEquals("Manual client",m.state.review!!.preview.fullName);assertEquals("Notes",m.state.review!!.preview.notes)
    }
    @Test fun identicalReviewRoundtripRejectsOldSubmitBackAndSourceEvent()=runTest {
        val port=Port(immediate=true);val m=model(port);m.open(m.entryControl);values(m);val edit=m.control!!;val input=m.inputControl!!;m.prepare(edit);val old=m.control!!;val review=m.state.review!!
        m.back(expected=m.returnControl);m.prepare(m.control);val current=m.control;m.submit(review,old);m.back(expected=ClientDraftReturnControl(edit,null));m.update(ClientDraftField.SOURCE,"instagram",input)
        assertEquals(review,m.state.review);assertNotEquals(old,current);assertEquals(current,m.control);assertTrue(port.attempts.isEmpty());assertEquals("telegram",m.state.values.source)
    }
    @Test fun clearConsentRejectsNewFieldEditReplacementAndClosedReopenedComposer() {
        val m=model();val entry=m.entryControl!!;m.open(entry);values(m);val control=m.control!!;val input=m.inputControl!!;m.askClear(control);val question=m.clearConfirmation!!
        m.update(ClientDraftField.NOTES,"Own newer description",input);m.confirmClear(question);assertNull(m.clearConfirmation);assertEquals("Own newer description",m.state.values.notes)
        m.askClear(control);val old=m.clearConfirmation!!;m.dismissClear(old);m.askClear(control);val current=m.clearConfirmation!!;m.dismissClear(old);m.confirmClear(old);m.back(expected=ClientDraftReturnControl(control,null));assertEquals(current,m.clearConfirmation)
        m.back(expected=m.returnControl);m.close(expected=m.returnControl);m.open(entry);assertNull(m.control);m.open(m.entryControl);m.confirmClear(current);assertEquals("Own newer description",m.state.values.notes)
        m.askClear(m.control);m.confirmClear(m.clearConfirmation!!);assertNull(m.control);assertEquals(ClientDraftValues(),m.state.values)
    }
    @Test fun pendingAttemptRevokesClearFieldEventsAndQueuedDuplicatesWhileBackRetainsIt()=runTest {
        val port=Port();val m=model(port,backgroundScope);m.open(m.entryControl);values(m);m.prepare(m.control);val control=m.control!!;val review=m.state.review!!;m.askClear(control);val consent=m.clearConfirmation!!
        val job=backgroundScope.launch {m.submit(review)};runCurrent();val record=m.submission!!;m.confirmClear(consent);m.askClear(m.control);m.update(ClientDraftField.FULL_NAME,"overwrite",ClientDraftInputControl(control));m.launchSubmit(review,control);runCurrent()
        assertNull(m.clearConfirmation);assertNull(m.inputControl);assertEquals(record,m.submission);assertEquals(review.values,m.state.values);assertEquals(1,port.attempts.size)
        m.back(expected=m.returnControl);assertNull(m.control);assertEquals(record,m.submission);m.open(m.entryControl);port.pending[0].complete(SyntheticClientCreateOutcome.Unknown);runCurrent();job.join();assertEquals(ClientCreateAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked)
    }
    @Test fun rejectedAcknowledgementRequiresCurrentTerminalVisitAndFreshReview()=runTest {
        val port=Port();val m=model(port);m.open(m.entryControl);values(m);m.prepare(m.control);val review=m.state.review!!;val old=m.control!!;val job=launch {m.submit(review,old)};runCurrent();val pending=m.control!!
        m.back(expected=m.returnControl);m.open(m.entryControl);val reopened=m.control!!;port.pending[0].complete(SyntheticClientCreateOutcome.RejectedWithoutWrite);job.join();val result=m.submission!!;val current=m.control!!
        m.acknowledge(pending,result);m.acknowledge(reopened,result);assertEquals(result,m.submission);m.acknowledge(current,result)
        assertFalse(m.submissionBlocked);assertEquals(review.values,m.state.values);assertEquals(ClientDraftPhase.EDITING,m.state.phase);assertEquals(1,m.retainedAttemptCount);m.submit(review,old);assertEquals(1,port.attempts.size)
        m.prepare(m.control);val second=launch {m.submit(m.state.review!!,m.control)};runCurrent();assertEquals(2,port.attempts.size);port.pending[1].complete(SyntheticClientCreateOutcome.Unknown);second.join()
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
        m.bind(ClientDraftContext(202,102));m.open(m.entryControl);val input=m.inputControl!!;val control=m.control;m.update(ClientDraftField.FULL_NAME,"Other Business raw",input);port.pending[0].complete(SyntheticClientCreateOutcome.Unknown);job.join()
        assertEquals(input,m.inputControl);assertEquals(control,m.control);assertEquals("Other Business raw",m.state.values.fullName);assertFalse(m.submissionBlocked);assertEquals(1,m.retainedAttemptCount)
        values(m);m.prepare(m.control);val canceled=launch {m.submit(m.state.review!!,m.control)};runCurrent();canceled.cancelAndJoin();assertEquals(ClientCreateAttemptPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.submissionBlocked)
    }
    @Test fun listOnlyControlsPreserveDraftSearchProfileAndTrustedExplicitSwitches()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val port=Port();val calls=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->calls+=r;ReadResponse(200,fixture("clients-101"))});val parent=ClientDirectoryViewModel(repo,port)
        try {
            parent.load(101,100);runCurrent();val list=parent.listControl!!;val rows=parent.state.items;val total=parent.state.total;val before=calls.toList();val m=parent.draft;val opening=m.entryControl!!
            assertTrue(parent.openDraftFromList(opening,list));values(m);val currentParent=parent.control!!;val forged=ClientDirectoryListControl(currentParent);val composer=m.control
            parent.searchList("hidden search",forged);parent.retryList(forged);assertFalse(parent.openSearchFromList(forged));assertFalse(parent.openList(701,forged));assertFalse(parent.openDraftFromList(opening,forged));runCurrent()
            assertEquals(currentParent,parent.control);assertNull(parent.listControl);assertEquals("",parent.state.query);assertEquals(composer,m.control);assertEquals(before,calls)
            m.prepare(m.control);val sending=m.control!!;val job=launch {m.submit(m.state.review!!,sending)};runCurrent();port.pending[0].complete(response(port.attempts[0]));job.join();val result=m.submission!!
            m.acknowledge(sending,result);assertTrue(m.submissionBlocked);m.acknowledge(m.control,result);assertNull(m.control);assertEquals(ClientDraftValues(),m.state.values);assertEquals(1,m.retainedAttemptCount)
            assertEquals(rows,parent.state.items);assertEquals(total,parent.state.total);assertEquals(before,calls);assertFalse(parent.openDraftFromList(opening,list));assertFalse(parent.openList(701,list));assertFalse(parent.openSearchFromList(list))
            assertTrue(parent.openSearchFromList(parent.listControl));val search=parent.serverSearch!!.state.selection;val searchParent=parent.control!!
            assertFalse(parent.openDraftFromList(m.entryControl,ClientDirectoryListControl(searchParent)));assertEquals(search,parent.serverSearch!!.state.selection)
            assertTrue(parent.openDraft(searchParent));assertNull(parent.serverSearch!!.state.selection);assertNotNull(m.control);assertTrue(parent.openSearch(parent.control));assertNull(m.control)
            assertTrue(parent.back(parent.control));assertTrue(parent.openList(701,parent.listControl));val profile=parent.control!!
            assertFalse(parent.openSearchFromList(ClientDirectoryListControl(profile)));assertFalse(parent.openDraftFromList(m.entryControl,ClientDirectoryListControl(profile)));assertEquals(701,parent.state.selectedID);assertEquals(before,calls)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
