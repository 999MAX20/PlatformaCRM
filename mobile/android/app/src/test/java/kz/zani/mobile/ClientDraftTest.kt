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
class ClientDraftTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    @Test fun emailMatchesPinnedExistingWebValidatorAndNeverRewritesInput() {
        val cases=JSONObject(fixture("client-draft-validation")).getJSONArray("email_cases")
        for (n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val raw=row.getString("email");val v=ClientDraftValues(fullName="Synthetic client",email=raw)
            assertEquals(raw,row.getBoolean("valid"),v.issues.none { it.field==ClientDraftField.EMAIL });assertEquals(raw,v.email)
        }
    }
    @Test fun fieldRulesComeFromExistingFormAndModelWithoutChangingNamesOrNotes() {
        assertTrue(ClientDraftValues(fullName=" ").issues.any { it.problem==ClientDraftProblem.NAME })
        assertTrue(ClientDraftValues(fullName="A").issues.any { it.problem==ClientDraftProblem.NAME })
        assertTrue(ClientDraftValues(fullName=" A ").issues.isEmpty())
        assertTrue(ClientDraftValues(fullName="Ә".repeat(255)).issues.isEmpty())
        assertTrue(ClientDraftValues(fullName="Ә".repeat(256)).issues.any { it.problem==ClientDraftProblem.NAME_LENGTH })
        assertTrue(ClientDraftValues(fullName="🙂".repeat(255)).issues.isEmpty())
        assertTrue(ClientDraftValues(fullName="Synthetic",phone="1".repeat(33)).issues.any { it.problem==ClientDraftProblem.PHONE_LENGTH })
        val notes="Synthetic note\n".repeat(2000)
        ClientDraftValues.sources.forEach { source -> val v=ClientDraftValues(fullName="Synthetic",phone="1".repeat(32),source=source,notes=notes);assertTrue(v.issues.isEmpty());assertEquals(notes,v.notes) }
        assertTrue(ClientDraftValues(fullName="Synthetic",source="unsupported").issues.any { it.problem==ClientDraftProblem.SOURCE })
    }
    @Test fun validationReviewBackCloseAndReopenRetainOnlyManualDraftValues() {
        val s=ClientDraftSession();val c=ClientDraftContext(101,1);assertFalse(s.open(c));s.bind(c);assertTrue(s.open(c));val first=s.state.selection!!
        s.update(ClientDraftField.FULL_NAME,"Synthetic client",first);s.update(ClientDraftField.EMAIL,"invalid address",first);s.update(ClientDraftField.NOTES,"Synthetic note",first)
        assertFalse(s.prepare(first));assertEquals("invalid address",s.state.values.email);assertEquals("Synthetic note",s.state.values.notes)
        s.update(ClientDraftField.EMAIL,"alpha@example.invalid",first);assertTrue(s.prepare(first));val review=s.state.review
        s.update(ClientDraftField.FULL_NAME,"late edit",first);assertEquals(review,s.state.review);assertEquals("Synthetic client",s.state.values.fullName)
        s.back(first);assertEquals(ClientDraftPhase.EDITING,s.state.phase);assertNull(s.state.review)
        s.back(first);assertEquals(ClientDraftPhase.CLOSED,s.state.phase);assertEquals("Synthetic client",s.state.values.fullName)
        assertTrue(s.open(c));val fresh=s.state.selection!!;assertNotEquals(first,fresh);s.update(ClientDraftField.FULL_NAME,"old input",first);s.discard(first)
        assertEquals(fresh,s.state.selection);assertEquals("Synthetic client",s.state.values.fullName)
        s.discard(fresh);assertEquals(ClientDraftValues(),s.state.values);assertNull(s.state.selection)
    }
    @Test fun businessEpochSwitchAndOldCallbacksCannotRestoreDiscardedForeignInput() {
        val s=ClientDraftSession();val a=ClientDraftContext(101,1);s.bind(a);s.open(a);val old=s.state.selection!!;s.update(ClientDraftField.FULL_NAME,"Synthetic A",old)
        s.bind(a);assertEquals(old,s.state.selection)
        val b=ClientDraftContext(202,2);s.bind(b);assertEquals(ClientDraftValues(),s.state.values);assertNull(s.state.selection)
        s.update(ClientDraftField.FULL_NAME,"foreign late",old);s.close(old);assertEquals(b,s.state.context);assertEquals(ClientDraftValues(),s.state.values)
        val roundTrip=ClientDraftContext(101,3);s.bind(roundTrip);s.open(roundTrip);val current=s.state.selection!!;s.discard(old);assertEquals(current,s.state.selection)
        s.bind(ClientDraftContext(0,4));assertNull(s.state.context);assertNull(s.state.selection)
    }
    @Test fun actualDirectoryDraftReviewDoesNotIssueRequestsCreateRowsOrLoseQuery()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport { r -> requests+=r;ReadResponse(200,fixture("clients-${r.query["business"]}")) });val model=ClientDirectoryViewModel(repo)
        try {
            model.load(101,7);runCurrent();model.search("Alpha");val rows=model.state.items;val draft=model.draft;val c=ClientDraftContext(101,7)
            draft.open(c);val selection=draft.state.selection!!;draft.update(ClientDraftField.FULL_NAME,"Synthetic local",selection);draft.update(ClientDraftField.NOTES,"Synthetic note",selection);draft.prepare(selection)
            assertEquals(ClientDraftPhase.REVIEW,draft.state.phase);assertEquals("manual",draft.state.review!!.values.source)
            assertEquals(rows,model.state.items);assertEquals("Alpha",model.state.query);assertNull(model.state.selectedID);assertEquals(1,requests.size)
            draft.back(selection);draft.back(selection);assertEquals("Synthetic local",draft.state.values.fullName)
            draft.open(c);val fresh=draft.state.selection!!;draft.discard(selection);assertEquals(fresh,draft.state.selection)
            model.back();assertNull(draft.state.selection);assertEquals("Synthetic note",draft.state.values.notes)
            model.load(202,8);assertEquals(ClientDraftValues(),draft.state.values);assertNull(draft.state.selection);runCurrent()
            draft.update(ClientDraftField.NOTES,"old event",fresh);assertTrue(draft.state.values.notes.isEmpty())
        } finally { model.viewModelScope.cancel();Dispatchers.resetMain() }
    }
    @Test fun sameContextReadErrorRetainsInputButNewContextInvalidatesBeforeResponse()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val pending=mutableListOf<CompletableDeferred<ClientList>>();val repo=ClientRepository { CompletableDeferred<ClientList>().also { pending+=it }.await() };val model=ClientDirectoryViewModel(repo)
        try {
            model.load(101,10);runCurrent();pending[0].complete(JsonContracts.clients(fixture("clients-101")));runCurrent()
            model.draft.open(ClientDraftContext(101,10));val selection=model.draft.state.selection!!;model.draft.update(ClientDraftField.FULL_NAME,"Retain after error",selection)
            model.load(101,10);runCurrent();pending[1].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));runCurrent()
            assertEquals("Retain after error",model.draft.state.values.fullName);assertEquals(selection,model.draft.state.selection)
            model.load(202,11);assertNull(model.draft.state.selection);assertTrue(model.draft.state.values.fullName.isEmpty());runCurrent()
            pending[2].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,model.state.problem);assertTrue(model.draft.state.values.fullName.isEmpty())
        } finally { model.viewModelScope.cancel();Dispatchers.resetMain() }
    }
}
