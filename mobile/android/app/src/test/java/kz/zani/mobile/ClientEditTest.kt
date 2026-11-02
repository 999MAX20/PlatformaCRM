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
class ClientEditTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun profile(business: Int=101,id: Int=701)=JsonContracts.clientProfile(fixture("client-$business-$id"))
    private val context=ClientEditContext(101,701,40)
    private fun origin()=profile().editReadFields!!.complete!!
    private fun changed(edit: (JSONObject)->Unit): ClientProfile {
        val json=JSONObject(fixture("client-101-701"));edit(json.getJSONObject("client"));return JsonContracts.clientProfile(json.toString())
    }
    private fun provider()=object: ClientEditOriginProvider {
        override suspend fun origin(profile: ClientProfile)=FixtureClientEditOriginProvider.verified(profile,this@ClientEditTest.profile(profile.business,profile.client.id))
    }
    @Test fun originalFourFieldsAreExactAndOnlyCompleteMatchingFixtureReferenceIsTrusted() {
        val p=profile();val o=origin()
        assertEquals(ClientEditValues("Synthetic Client Alpha","+70000000001","alpha@example.invalid","manual"),o.values)
        assertEquals(o,FixtureClientEditOriginProvider.verified(p,p))
        assertFalse(ClientEditValues.fields.contains(ClientDraftField.NOTES))
        val blank=changed {it.put("phone","");it.put("email","")}
        assertEquals("",blank.editReadFields!!.complete!!.values.phone);assertEquals("",blank.editReadFields.complete!!.values.email)
        assertNull(FixtureClientEditOriginProvider.verified(blank,p))
        listOf("title","phone","email","source","updated_at").forEach {key->
            assertNull(changed {it.remove(key)}.editReadFields!!.complete)
            assertNull(changed {it.put(key,JSONObject.NULL)}.editReadFields!!.complete)
        }
        listOf(changed {it.put("phone","+7***0001")},changed {it.put("source","telegram")},changed {it.put("updated_at","new-version")}).forEach {assertNull(FixtureClientEditOriginProvider.verified(it,p))}
        assertNull(changed {it.put("source","unsupported")}.editReadFields!!.complete)
        val unknown=ClientEditReadFields("Synthetic",null,"","manual","v1");assertNull(unknown.complete)
        assertNull(unknown.copy(phone="",source=null).complete);assertNull(unknown.copy(phone="",version="").complete)
        val json=JSONObject(fixture("client-101-701"));val notes="Synthetic private note\n".repeat(3000)
        json.getJSONObject("client").put("notes",notes.take(160));json.getJSONObject("details").put("notes",notes.take(1000))
        assertEquals(o,FixtureClientEditOriginProvider.verified(JsonContracts.clientProfile(json.toString()),p))
    }
    @Test fun existingValidationDiffReviewBackReopenAndExplicitCancelPreserveExactOriginal() {
        val s=ClientEditSession();val original=origin();assertFalse(s.open(context));s.begin(context);assertFalse(s.open(context))
        s.receive(original,context);assertTrue(s.open(context));val first=s.state.selection!!
        assertTrue(s.prepare(first));assertTrue(s.state.review!!.changed.isEmpty());s.back(first)
        s.update(ClientDraftField.FULL_NAME,"Synthetic changed",first);s.update(ClientDraftField.EMAIL,"bad address",first);s.update(ClientDraftField.NOTES,"Do not edit truncated notes",first)
        assertFalse(s.prepare(first));assertEquals("bad address",s.state.values!!.email)
        s.update(ClientDraftField.EMAIL,original.values.email,first);assertTrue(s.prepare(first));val review=s.state.review!!
        assertEquals(listOf(ClientDraftField.FULL_NAME),review.changed);assertEquals(original.values,review.original);assertEquals("Synthetic changed",review.values.fullName)
        s.update(ClientDraftField.PHONE,"late review",first);assertEquals(review,s.state.review)
        s.back(first);s.back(first);assertNull(s.state.selection);assertEquals("Synthetic changed",s.state.values!!.fullName)
        s.open(context);val reopened=s.state.selection!!;s.cancel(first);s.update(ClientDraftField.FULL_NAME,"stale",first);assertEquals(reopened,s.state.selection)
        s.cancel(reopened);assertEquals(original.values,s.state.values);assertNull(s.state.selection);assertFalse(s.hasStoredChanges)
        val bad=original.values.copy(fullName="A",phone="1".repeat(33),email="bad address",source="unsupported")
        assertEquals(ClientEditValues.fields.toSet(),bad.issues.map {it.field}.toSet())
        assertTrue(original.values.copy(fullName="🙂".repeat(255)).issues.isEmpty());assertTrue(original.values.copy(fullName="🙂".repeat(256)).issues.any {it.problem==ClientDraftProblem.NAME_LENGTH})
        ClientDraftValues.sources.forEach {assertTrue(original.values.copy(source=it,phone="1".repeat(32)).issues.isEmpty())}
    }
    @Test fun hiddenRamBuffersBelongToOneClientBusinessEpochAndRequireFreshMatchingOrigin() {
        val s=ClientEditSession();val original=origin();s.begin(context);s.receive(original,context);s.open(context);val first=s.state.selection!!
        s.update(ClientDraftField.FULL_NAME,"Client A unsent",first);s.pause();assertNull(s.state.values);assertNull(s.state.context)
        s.begin(context);assertNull(s.state.values);s.receive(original,context);assertEquals("Client A unsent",s.state.values!!.fullName)
        val other=context.copy(client=702);s.begin(other);s.receive(original,other);assertEquals(original.values,s.state.values)
        s.open(other);s.update(ClientDraftField.PHONE,"Client B phone",s.state.selection!!)
        s.begin(context);s.receive(original,context);assertEquals("Client A unsent",s.state.values!!.fullName);assertEquals(original.values.phone,s.state.values!!.phone)
        val epoch=context.copy(epoch=41);s.begin(epoch);s.receive(original,context);assertNull(s.state.values);s.receive(original,epoch);assertEquals(original.values,s.state.values)
        s.open(epoch);s.update(ClientDraftField.FULL_NAME,"Epoch input",s.state.selection!!)
        val business=epoch.copy(business=202);s.begin(business);s.receive(original,business);assertEquals(original.values,s.state.values)
        s.update(ClientDraftField.FULL_NAME,"late",first);assertEquals(original.values,s.state.values)
        s.begin(context.copy(business=0));assertNull(s.state.context);assertNull(s.state.values)
    }
    @Test fun changedOrUnknownOriginQuarantinesInputUntilExplicitDiscardWithoutSilentRebase() {
        val s=ClientEditSession();val original=origin();s.begin(context);s.receive(original,context);s.open(context)
        s.update(ClientDraftField.PHONE,"Unsent phone",s.state.selection!!)
        val changed=original.copy(version="v2");s.begin(context);s.receive(changed,context)
        assertTrue(s.state.needsReset);assertTrue(s.hasStoredChanges);assertFalse(s.state.available);assertNull(s.state.values);assertFalse(s.open(context))
        s.discardStored(context.copy(client=702));assertTrue(s.state.needsReset)
        s.discardStored(context);assertEquals(changed,s.state.origin);assertEquals(original.values,s.state.values);assertFalse(s.hasStoredChanges)
        s.open(context);s.update(ClientDraftField.EMAIL,"local@example.invalid",s.state.selection!!)
        s.begin(context);s.receive(original.copy(values=original.values.copy(phone="new independent phone")),context)
        assertTrue(s.state.needsReset);assertNull(s.state.values)
        s.receive(null,context);assertTrue(s.state.needsReset);assertNull(s.state.values)
        s.discardStored(context);assertNull(s.state.values);assertFalse(s.state.available);assertFalse(s.hasStoredChanges)
    }
    @Test fun actualIndependentProfileEditIssuesNoExtraRequestsAndNeverMutatesDirectoryOrSource()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->requests+=r;ReadResponse(200,fixture(if(r.path.endsWith("clients/"))"clients-101" else "client-101-701"))})
        val list=ClientDirectoryViewModel(repo);val model=ClientProfileViewModel(repo,editOriginSource=provider());val opaque=ClientProfileViewModel(repo)
        try {
            list.load(101,10);runCurrent();list.search("Alpha");list.open(701);var accepted=0
            model.loadScoped(101,701,10) {b,c->accepted++;list.refreshContact(b,c)};runCurrent()
            val rows=list.state.items;val readCount=requests.size;val source=model.state.detail;val edit=model.edit!!;val c=ClientEditContext(101,701,10)
            edit.open(c);val selection=edit.state.selection!!;edit.update(ClientDraftField.FULL_NAME,"Synthetic unsent edit",selection);edit.prepare(selection)
            assertEquals(ClientDraftPhase.REVIEW,edit.state.phase);assertEquals(listOf(ClientDraftField.FULL_NAME),edit.state.review!!.changed)
            assertEquals(readCount,requests.size);assertEquals(1,accepted);assertEquals(rows,list.state.items);assertEquals("Alpha",list.state.query);assertEquals(701,list.state.selectedID);assertEquals(source,model.state.detail)
            model.clear();assertNull(edit.state.values);model.loadScoped(101,701,10);runCurrent();assertEquals("Synthetic unsent edit",edit.state.values!!.fullName)
            opaque.loadScoped(101,701,10);runCurrent();assertNull(opaque.edit)
            model.load(101,701);runCurrent();assertNull(edit.state.context);assertFalse(edit.state.available)
        } finally {model.viewModelScope.cancel();opaque.viewModelScope.cancel();list.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private class Controlled: ClientProfileRepository {
        val pending=mutableListOf<CompletableDeferred<ClientProfile>>()
        override suspend fun clientProfile(business: Int,id: Int)=CompletableDeferred<ClientProfile>().also {pending+=it}.await()
    }
    @Test fun deniedUnavailableAndMaskedRetryHideInputAndMatchingRecoveryRestoresOwnDraft()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();val model=ClientProfileViewModel(repo,editOriginSource=provider())
        try {
            model.loadScoped(101,701,40);runCurrent();repo.pending[0].complete(profile());runCurrent();val edit=model.edit!!;edit.open(context)
            edit.update(ClientDraftField.PHONE,"Unsent phone",edit.state.selection!!)
            listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).forEachIndexed {n,problem->
                model.loadScoped(101,701,40);assertNull(edit.state.values);runCurrent();repo.pending[1+n*2].completeExceptionally(ReadException(problem));runCurrent()
                assertEquals(problem,model.state.problem);assertNull(model.state.detail);assertFalse(edit.state.available)
                model.loadScoped(101,701,40);runCurrent();repo.pending[2+n*2].complete(profile());runCurrent();assertEquals("Unsent phone",edit.state.values!!.phone)
            }
            model.loadScoped(101,701,40);runCurrent();repo.pending[5].complete(changed {it.put("phone","+7***0001")});runCurrent()
            assertEquals("+7***0001",model.state.detail!!.client.phone);assertTrue(edit.state.needsReset);assertNull(edit.state.values)
            edit.discardStored(context);assertFalse(edit.state.available);assertNull(edit.state.values)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateOriginProviderCannotPublishOldClientBusinessEpochOrClosedProfile()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val pending=mutableListOf<CompletableDeferred<ClientEditOrigin?>>()
        val source=object: ClientEditOriginProvider {override suspend fun origin(profile: ClientProfile)=CompletableDeferred<ClientEditOrigin?>().also {pending+=it}.await()}
        val repo=object: ClientProfileRepository {override suspend fun clientProfile(business: Int,id: Int)=profile(business,id)}
        val model=ClientProfileViewModel(repo,editOriginSource=source)
        try {
            val accepted=mutableListOf<Int>();model.loadScoped(101,701,30) {_,c->accepted+=c.id};runCurrent();model.loadScoped(202,801,31) {_,c->accepted+=c.id};runCurrent()
            val other=profile(202,801).editReadFields!!.complete;assertNull(other);pending[1].complete(other);runCurrent();pending[0].complete(origin());runCurrent()
            assertEquals(listOf(801),accepted);assertEquals(801,model.state.detail!!.client.id);assertEquals(other,model.edit!!.state.origin);assertFalse(model.edit!!.state.available)
            model.loadScoped(101,701,32);runCurrent();model.loadScoped(101,701,33);runCurrent();pending[2].complete(origin());runCurrent()
            assertTrue(model.state.loading);assertNull(model.state.detail);assertNull(model.edit!!.state.values)
            pending[3].complete(origin());runCurrent();assertEquals(33,model.state.scopeEpoch);assertEquals(origin().values,model.edit!!.state.values)
            model.loadScoped(101,701,33);runCurrent();model.clear();pending[4].complete(origin());runCurrent();assertNull(model.state.detail);assertNull(model.edit!!.state.values)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateIndependentProfileResponseCannotRestorePriorBusinessEdit()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=ClientProfileViewModel(source,editOriginSource=provider())
        try {
            model.loadScoped(101,701,40);runCurrent();model.loadScoped(202,801,41);runCurrent()
            source.pending[1].complete(profile(202,801));runCurrent();source.pending[0].complete(profile());runCurrent()
            assertEquals(801,model.state.detail!!.client.id);assertEquals(ClientEditContext(202,801,41),model.edit!!.state.context)
            assertEquals(profile(202,801).editReadFields!!.complete,model.edit!!.state.origin)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
