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
class ClientEditControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun profile()=JsonContracts.clientProfile(fixture("client-101-701"))
    private fun origin()=profile().editReadFields!!.complete!!
    private val context=ClientEditContext(101,701,9)
    private fun model()=ClientEditModel().also {it.begin(context);it.receive(origin(),context)}
    @Test fun unresolvedEntryDuplicateOpenAndContinuousValidationKeepExactInput() {
        val edit=ClientEditModel();edit.open(null as ClientEditEntryControl?);edit.prepare(null as ClientEditControl?);edit.askCancel(null);edit.askDiscard(null)
        assertNull(edit.control);assertNull(edit.confirmation);edit.begin(context);val unresolved=edit.entryControl!!;edit.open(unresolved);assertNull(edit.control)
        edit.receive(origin(),context);edit.open(unresolved);assertNull(edit.control)
        val entry=edit.entryControl!!;edit.open(entry);val first=edit.control!!;val input=edit.inputControl!!
        edit.open(entry);assertEquals(first,edit.control)
        edit.update(ClientDraftField.FULL_NAME,"Synthetic first",input);edit.update(ClientDraftField.PHONE,"Synthetic phone",input)
        assertEquals(input,edit.inputControl);assertEquals("Synthetic phone",edit.state.values!!.phone)
        edit.update(ClientDraftField.EMAIL,"bad address",input);edit.prepare(first)
        assertEquals(first,edit.control);assertTrue(edit.state.issues.isNotEmpty());assertEquals(ClientDraftPhase.EDITING,edit.state.phase)
        edit.update(ClientDraftField.EMAIL,origin().values.email,input);edit.prepare(first)
        assertEquals(ClientDraftPhase.REVIEW,edit.state.phase);assertEquals(origin().values,edit.state.review!!.original);assertNull(edit.inputControl)
    }
    @Test fun staleInputBackCloseAndSameSelectionReviewCannotReachNewPhase() {
        val edit=model();edit.open(edit.entryControl);val first=edit.control!!;val input=edit.inputControl!!
        edit.update(ClientDraftField.FULL_NAME,"Synthetic first",input);edit.prepare(first);val review=edit.control!!;val snapshot=edit.state.review
        edit.update(ClientDraftField.PHONE,"late input",input);edit.back(first);edit.close(first);edit.prepare(first)
        assertEquals(review,edit.control);assertEquals(snapshot,edit.state.review);assertEquals(origin().values.phone,edit.state.values!!.phone)
        edit.back(review);val editing=edit.control!!;edit.update(ClientDraftField.FULL_NAME,"Synthetic second",edit.inputControl);edit.prepare(editing);val review2=edit.control!!
        edit.back(review);edit.close(review);edit.askCancel(review)
        assertEquals(review.selection,review2.selection);assertNotEquals(review,review2);assertEquals(review2,edit.control);assertNull(edit.confirmation)
    }
    @Test fun changedInputAndReplacementDialogRejectOldDestructiveConsent() {
        val edit=model();edit.open(edit.entryControl);val control=edit.control!!;val input=edit.inputControl!!
        edit.update(ClientDraftField.FULL_NAME,"Synthetic first",input);edit.askCancel(control);val question=edit.confirmation!!
        edit.update(ClientDraftField.FULL_NAME,"Synthetic newer",input);edit.confirm(question)
        assertNull(edit.confirmation);assertEquals("Synthetic newer",edit.state.values!!.fullName);assertEquals(control,edit.control)
        edit.askCancel(control);val old=edit.confirmation!!;edit.dismiss(old);edit.askCancel(control);val current=edit.confirmation!!
        edit.dismiss(old);edit.confirm(old);assertNotEquals(old,current);assertEquals(current,edit.confirmation);assertTrue(edit.hasStoredChanges)
        edit.confirm(current);assertNull(edit.control);assertEquals(origin().values,edit.state.values);assertFalse(edit.hasStoredChanges)
    }
    @Test fun closeAndReopenPreserveOwnBufferWhileOldEntryInputAndConsentStayRevoked() {
        val edit=model();val entry=edit.entryControl!!;edit.open(entry);val first=edit.control!!;val input=edit.inputControl!!
        edit.update(ClientDraftField.PHONE,"Own unsent phone",input);edit.askCancel(first);val question=edit.confirmation!!;edit.dismiss(question);edit.close(first)
        assertEquals("Own unsent phone",edit.state.values!!.phone);assertTrue(edit.hasStoredChanges)
        edit.open(entry);assertNull(edit.control);edit.open(edit.entryControl);val current=edit.control
        edit.confirm(question);edit.update(ClientDraftField.PHONE,"stale input",input);edit.back(first)
        assertEquals(current,edit.control);assertEquals("Own unsent phone",edit.state.values!!.phone)
        edit.pause();assertNull(edit.state.values);edit.begin(context);edit.receive(origin(),context);assertEquals("Own unsent phone",edit.state.values!!.phone)
    }
    @Test fun sameContextOriginRoundtripAndReplacementResetKeepQuarantinedDraft() {
        val edit=model();edit.open(edit.entryControl);edit.update(ClientDraftField.PHONE,"Own unsent phone",edit.inputControl)
        val changed=origin().copy(version="synthetic v2");edit.receive(changed,context);val entry=edit.entryControl!!;edit.askDiscard(entry);val old=edit.confirmation!!
        assertTrue(edit.state.needsReset);assertNull(edit.state.values);edit.receive(null,context);edit.confirm(old);assertTrue(edit.hasStoredChanges)
        edit.receive(origin(),context);assertEquals("Own unsent phone",edit.state.values!!.phone);edit.receive(changed,context);edit.askDiscard(entry);assertNull(edit.confirmation)
        edit.askDiscard(edit.entryControl);val replaced=edit.confirmation!!;edit.dismiss(replaced);edit.askDiscard(edit.entryControl);val current=edit.confirmation!!
        edit.confirm(replaced);edit.dismiss(replaced);assertEquals(current,edit.confirmation);assertTrue(edit.hasStoredChanges)
        edit.confirm(current);assertEquals(changed,edit.state.origin);assertEquals(changed.values,edit.state.values);assertFalse(edit.hasStoredChanges)
        edit.open(edit.entryControl);edit.update(ClientDraftField.PHONE,"Unknown retained",edit.inputControl);edit.receive(null,context);edit.askDiscard(edit.entryControl);edit.confirm(edit.confirmation!!)
        assertNull(edit.state.values);assertFalse(edit.state.available);assertFalse(edit.hasStoredChanges)
    }
    @Test fun oldOwnerReplyActionsAndConsentCannotTouchNewEpoch() {
        val edit=model();edit.open(edit.entryControl);val old=edit.control!!;val input=edit.inputControl!!
        edit.update(ClientDraftField.FULL_NAME,"Private old owner",input);edit.askCancel(old);val question=edit.confirmation!!
        val next=context.copy(epoch=10);edit.begin(next);val pending=edit.entryControl;edit.receive(origin(),context);assertEquals(pending,edit.entryControl);assertFalse(edit.state.available)
        edit.receive(origin(),next);edit.open(edit.entryControl);val current=edit.control;edit.confirm(question);edit.back(old);edit.update(ClientDraftField.PHONE,"stale",input)
        assertEquals(current,edit.control);assertEquals(origin().values,edit.state.values);edit.pause();edit.confirm(question);assertNull(edit.control);assertNull(edit.entryControl);assertNull(edit.state.values)
    }
    @Test fun capturedParentBackDistinguishesReviewDialogAndReopenedEditorWithoutClosingProfile()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {r->requests+=r;ReadResponse(200,fixture("client-101-701"))})
        val source=object:ClientEditOriginProvider {override suspend fun origin(profile:ClientProfile)=FixtureClientEditOriginProvider.verified(profile,this@ClientEditControlsTest.profile())}
        val parent=ClientProfileViewModel(repo,editOriginSource=source)
        try {
            parent.loadScoped(101,701,9);runCurrent();val edit=parent.edit!!;val profile=parent.state.detail;val read=parent.readSelection;val before=requests.size
            val entry=parent.workReturnControl;edit.open(edit.entryControl);val editing=parent.workReturnControl
            assertFalse(parent.backEdit(entry));assertNotNull(edit.control)
            edit.update(ClientDraftField.FULL_NAME,"Synthetic own name",edit.inputControl);edit.prepare(edit.control);val review=parent.workReturnControl
            assertFalse(parent.backEdit(editing));assertEquals(ClientDraftPhase.REVIEW,edit.state.phase)
            edit.askCancel(edit.control);val dialog=parent.workReturnControl;assertFalse(parent.backEdit(review));assertNotNull(edit.confirmation)
            assertTrue(parent.backEdit(dialog));assertNull(edit.confirmation);assertEquals(ClientDraftPhase.REVIEW,edit.state.phase)
            assertFalse(parent.backEdit(dialog));assertTrue(parent.backEdit(parent.workReturnControl));assertEquals(ClientDraftPhase.EDITING,edit.state.phase)
            val old=parent.workReturnControl;assertTrue(parent.backEdit(old));assertNull(edit.control);edit.open(edit.entryControl);assertFalse(parent.backEdit(old));assertNotNull(edit.control)
            assertEquals("Synthetic own name",edit.state.values!!.fullName);assertEquals(profile,parent.state.detail);assertEquals(read,parent.readSelection);assertEquals(before,requests.size)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
