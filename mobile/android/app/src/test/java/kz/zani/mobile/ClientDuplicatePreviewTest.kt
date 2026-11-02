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
class ClientDuplicatePreviewTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun exactResponseFieldsAndExplicitFixtureLookupNeverNormalizeOrGrant()=runTest {
        val catalog=JSONObject(fixture("client-duplicate-preview"));val cases=catalog.getJSONArray("decode_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val parsed=runCatching {ClientDuplicateResponse.decode(row.getString("response_json"))}.getOrNull()
            assertEquals(row.getString("name"),row.getBoolean("valid"),parsed!=null)
            parsed?.duplicates?.forEachIndexed {i,item->val raw=JSONObject(row.getString("response_json")).getJSONArray("duplicates").getJSONObject(i);assertEquals(raw.getString("full_name"),item.fullName);assertEquals(raw.getString("phone"),item.phone);assertEquals(raw.getString("email"),item.email)}
        }
        val source=FixtureClientDuplicatePreviewSource.fromFixture(fixture("client-duplicate-preview"));val c=ClientDraftContext(101,9)
        assertEquals(701,source.preview(ClientDuplicatePreviewInput(c,"+70000000000",""))!!.duplicates.first().id)
        assertEquals(801,source.preview(ClientDuplicatePreviewInput(ClientDraftContext(202,9),"+70000000000",""))!!.duplicates.first().id)
        assertNull(source.preview(ClientDuplicatePreviewInput(c,"+70000000000 ","")))
        assertNull(source.preview(ClientDuplicatePreviewInput(c,"","ALPHA@example.invalid")))
        assertNull(source.preview(ClientDuplicatePreviewInput(ClientDraftContext(0,9),"+70000000000","")))
        assertNotEquals(ClientDuplicatePreviewInput(c,"é",""),ClientDuplicatePreviewInput(c,"e\u0301",""))
    }
    @Test fun actualDraftReviewRetainsInputAndRevokesLateSourceAcrossReviewAndBusiness()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val requests=mutableListOf<ReadRequest>();val source=FixtureClientDuplicatePreviewSource.fromFixture(fixture("client-duplicate-preview"))
        val owner=ClientDirectoryViewModel(APIReadRepository(ReadTransport {r->requests+=r;ReadResponse(200,fixture("clients-${r.query["business"]}"))}),duplicateSource=source)
        try {
            owner.load(101,9);runCurrent();val rows=owner.state.items;val reads=requests.size;val model=owner.draft;val c=ClientDraftContext(101,9)
            model.open(c);val selection=model.state.selection!!;model.update(ClientDraftField.FULL_NAME,"Unsent owner input",selection);model.update(ClientDraftField.PHONE,"+70000000000",selection);model.update(ClientDraftField.NOTES,"Private unsent note",selection);model.prepare(selection)
            val control=model.control!!;val visit=model.duplicates!!.visit;val review=model.state.review;model.loadDuplicates(control,visit)
            assertEquals(701,model.duplicates!!.result!!.duplicates.first().id);assertEquals(review,model.state.review);assertFalse(model.canSubmit);assertEquals(0,model.retainedAttemptCount);assertEquals(rows,owner.state.items);assertEquals(reads,requests.size)
            val loaded=model.duplicates!!.visit;model.loadDuplicates(control,visit);assertEquals(loaded,model.duplicates!!.visit)
            model.back(selection);assertNull(model.duplicates!!.result);assertEquals("Private unsent note",model.state.values.notes);model.prepare(selection);model.loadDuplicates(control,loaded);assertNull(model.duplicates!!.result)
            model.loadDuplicates(model.control,model.duplicates!!.visit);model.askClear(model.control);assertNull(model.duplicates!!.result);assertEquals("Private unsent note",model.state.values.notes);model.dismissClear(model.clearConfirmation!!)
            val pending=mutableListOf<CompletableDeferred<ClientDuplicateResponse?>>()
            val held=object:SyntheticClientDuplicatePreviewSource {override suspend fun preview(input:ClientDuplicatePreviewInput)=CompletableDeferred<ClientDuplicateResponse?>().also {pending+=it}.await()}
            val late=ClientDraftModel(ownerScope=this,duplicateSource=held);late.bind(c);late.open(c);val old=late.state.selection!!;late.update(ClientDraftField.FULL_NAME,"Held draft",old);late.prepare(old)
            val call=launch {late.loadDuplicates(late.control,late.duplicates!!.visit)};runCurrent();assertTrue(late.duplicates!!.loading)
            late.back(old);late.prepare(old);val next=late.control;pending[0].complete(source.preview(ClientDuplicatePreviewInput(c,"+70000000000","")));runCurrent();call.join()
            assertEquals(next,late.control);assertNull(late.duplicates!!.result);assertFalse(late.duplicates!!.loading);assertEquals("Held draft",late.state.values.fullName)
            val second=launch {late.loadDuplicates(next,late.duplicates!!.visit)};runCurrent();late.bind(ClientDraftContext(202,10));pending[1].complete(source.preview(ClientDuplicatePreviewInput(c,"+70000000000","")));runCurrent();second.join();assertNull(late.duplicates!!.result);assertEquals("",late.state.values.fullName)
            val readOnly=ClientDraftModel();assertNull(readOnly.duplicates);assertFalse(readOnly.canSubmit)
            val empty=ClientDuplicatePreviewModel(source);empty.load(ClientDuplicatePreviewInput(c,"",""),empty.visit);assertTrue(empty.result!!.duplicates.isEmpty());assertNull(empty.problem)
            empty.load(ClientDuplicatePreviewInput(c,"missing",""),empty.visit);assertNull(empty.result);assertEquals(ReadProblem.UNAVAILABLE,empty.problem)
            val unknownPort=object:SyntheticClientCreatePort {
                override val grants=listOf(SyntheticClientCreateGrant(101,5001,true))
                override suspend fun execute(attempt:ClientCreateAttempt):SyntheticClientCreateOutcome=SyntheticClientCreateOutcome.Unknown
            }
            val unknown=ClientDraftModel(unknownPort,this,source);unknown.bind(c);unknown.open(c);val us=unknown.state.selection!!;unknown.update(ClientDraftField.FULL_NAME,"Unknown unsent owner",us);unknown.update(ClientDraftField.PHONE,"+70000000000",us);unknown.prepare(us)
            val uc=unknown.control!!;unknown.loadDuplicates(uc,unknown.duplicates!!.visit);assertNotNull(unknown.duplicates!!.result);unknown.submit(unknown.state.review!!,uc)
            val retained=unknown.submission!!;assertEquals(ClientCreateAttemptPhase.UNKNOWN,retained.phase);assertEquals(1,unknown.retainedAttemptCount);assertNull(unknown.duplicates!!.result);assertEquals("Unknown unsent owner",unknown.state.values.fullName)
            unknown.loadDuplicates(unknown.control,unknown.duplicates!!.visit);assertEquals(retained,unknown.submission);assertEquals(1,unknown.retainedAttemptCount);assertFalse(unknown.canSubmit);assertNull(unknown.duplicates!!.result)
            val denied=ClientDuplicatePreviewModel(object:SyntheticClientDuplicatePreviewSource {override suspend fun preview(input:ClientDuplicatePreviewInput):ClientDuplicateResponse? {throw ReadException(ReadProblem.DENIED)}})
            denied.load(ClientDuplicatePreviewInput(c,"",""),denied.visit);assertEquals(ReadProblem.DENIED,denied.problem);assertNull(denied.result)
        } finally {owner.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
