package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AppointmentBookingClientTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun source():AppointmentBookingSource {val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap")));val p=JsonContracts.appointments(fixture("appointments-101"));val scope=s.begin(101,p.date);s.receive(p,scope);return AppointmentBookingSource(s.beginDetail(501),1,7001,8001,9001)}
    private fun transport(log:MutableList<ReadRequest> = mutableListOf())=ReadTransport {q->
        log+=q;val id=q.path.trimEnd('/').substringAfterLast('/');val business=q.query["business"]?.toInt() ?: 101
        when {
            q.path=="/api/mobile/v1/clients/" && q.query.containsKey("search")->FixtureClientSearch.list(fixture("client-search-catalogue-$business"),business,q.query["search"]!!)
            q.path.startsWith("/api/mobile/v1/clients/") && id.toIntOrNull()?.let {FixtureClientSearch.isCatalogueID(it)}==true->FixtureClientSearch.profile(fixture("client-search-catalogue-$business"),business,id.toInt())
            else->{val name=when {q.path.startsWith("/api/services/")->"service-reference-$id";q.path.startsWith("/api/resources/")->"resource-reference-$id";q.path.startsWith("/api/mobile/v1/clients/")->"client-$business-$id";else->error("Unexpected read")};ReadResponse(200,fixture(name))}
        }
    }
    private fun port()=FixtureAppointmentBookingPort.fromJSON(fixture("appointment-booking"))
    private class ActorPort(override var grants:List<SyntheticAppointmentBookingGrant>):SyntheticAppointmentBookingPort {override suspend fun execute(attempt:AppointmentBookingAttempt):SyntheticAppointmentBookingOutcome=SyntheticAppointmentBookingOutcome.Unknown}
    @Test fun sharedProfileScopeRawWithheldLegacyAndFiveFieldBody()=runTest {
        val base=source();val repo=APIReadRepository(transport());val refs=APIAppointmentReferenceRepository(transport());val service=refs.reference(AppointmentReferenceKind.SERVICE,101,8001)
        fun profile(id:Int,business:Int,title:Any):ClientProfile {val o=JSONObject(fixture("client-101-7002"));o.put("business",business);o.getJSONObject("client").put("id",id).put("title",title);return JsonContracts.clientProfile(o.toString())}
        val cases=JSONObject(fixture("appointment-booking-client")).getJSONArray("cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val s=base.copy(epoch=row.getInt("source_epoch"));val ps=base.copy(epoch=row.getInt("proof_source_epoch"));val context=ClientSearchContext(row.getInt("context_business"),row.getInt("context_epoch"));val selection=ClientSearchSelection(context,row.getInt("selection_generation"));val selected=ClientSearchProfileSelection(selection,row.getInt("selected_id"),row.getInt("profile_generation"));val read=ClientReadSelection(row.getInt("read_business"),row.getInt("read_id"),row.getInt("read_revision"))
            val proof=if(row.getBoolean("proof"))AppointmentBookingClientSelection.make(ps,selected,read,row.getString("raw_query"),profile(row.getInt("profile_id"),row.getInt("profile_business"),row.get("proof_title")))else null
            val client=TaskDraftClientChoice.make(profile(row.getInt("client"),101,row.get("client_title")),101,row.getInt("client"))!!
            val input=if(row.getBoolean("proof") && proof==null)null else AppointmentBookingInput.prepare(s,client,service,AppointmentRescheduleResource.Clear,"2026-10-29T05:00:00Z",clientSelection=proof)
            assertEquals(row.getString("name"),row.getBoolean("valid"),input!=null)
            if(input!=null) {assertTrue(input.valid(s));val body=JSONObject(input.body(101)!!);assertEquals(setOf("business","client","service","start_at","resource"),body.keys().asSequence().toSet());assertEquals(client.id,body.getInt("client"))}
        }
        val selected=ClientSearchProfileSelection(ClientSearchSelection(ClientSearchContext(101,1),1),1754,1);val read=ClientReadSelection(101,1754,1);val p=repo.clientProfile(101,1754)
        val proof=AppointmentBookingClientSelection.make(base,selected,read,"é",p)!!;assertNotEquals(proof,AppointmentBookingClientSelection.make(base,selected,read,"e\u0301",p))
        val input=AppointmentBookingInput.prepare(base,proof.choice,service,AppointmentRescheduleResource.Clear,"2026-10-29T05:00:00Z",clientSelection=proof)!!;val review=AppointmentBookingReview(base,input,1);val auth=SyntheticAppointmentBookingGrant(101,501,5001,true).authorization(base)!!
        assertNull(SyntheticAppointmentBookingGrant(101,501,5001,false).authorization(base));val ledger=AppointmentBookingLedger();val attempt=ledger.begin(review,auth)!!;val receipt=JSONObject(JSONObject(fixture("appointment-booking")).getJSONArray("scenarios").getJSONObject(0).getString("response_json")).put("client",1754)
        ledger.complete(attempt,SyntheticAppointmentBookingOutcome.Response(201,receipt.toString()));assertEquals(AppointmentBookingPhase.ACCEPTED_FIXTURE,ledger.records[0].phase);assertEquals(proof,ledger.records[0].attempt.review.input.clientSelection)
        val unknown=AppointmentBookingLedger();val retained=unknown.begin(review,auth)!!;unknown.complete(retained,SyntheticAppointmentBookingOutcome.Unknown);assertEquals(proof.choice,TaskDraftClientChoice.make(repo.clientProfile(101,1754),101,1754));assertTrue(unknown.blocked(base));assertNull(unknown.begin(review,auth));assertFalse(unknown.acknowledge(unknown.records[0]));assertEquals(retained,unknown.records[0].attempt)
    }
    @Test fun actualPrivateManualQueryProfileUseReviewAndUnknown()=runTest {
        val log=mutableListOf<ReadRequest>();val repo=APIReadRepository(transport(log));val b=AppointmentBookingModel(port(),repo,APIAppointmentReferenceRepository(transport()),clientChoices=ClientSearchModel(repo,this));val s=source();b.bind(s);b.open(b.control);b.setStart("2026-10-29T05:00:00Z",b.inputControl);b.load(AppointmentBookingReadKind.SERVICE,b.control);b.chooseClear(b.control)
        val search=b.clientChoices!!;val oldInput=b.inputControl;val oldAction=b.control;val before=log.size;b.openClientPicker(b.control,search.control);val owner=b.clientPickerOwner!!;val input=search.inputControl!!;val first=search.control!!
        assertFalse(b.editing);assertNull(b.inputControl);assertFalse(search.state.loaded);assertEquals(before,log.size);b.setStart("stale",oldInput);b.load(AppointmentBookingReadKind.CLIENT,oldAction);assertNull(b.client)
        search.update("é",input);search.update("e\u0301",input);assertEquals("e\u0301",search.state.query);assertEquals(input,search.inputControl);search.submit(first);runCurrent();assertEquals(before,log.size)
        val raw=" \u2007 \t";search.update(raw,input);search.submit(search.control);runCurrent();assertTrue(search.state.partial);assertFalse(search.state.showsEmpty);assertEquals(50,search.state.items.size);assertEquals(56,search.state.total);assertTrue(b.matchesClientPicker(owner));assertEquals(ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "101","limit" to "50","search" to "")),log.last())
        val list=search.control;search.openClient(1754,list);runCurrent();val leaf=search.control;assertEquals(ReadRequest("/api/mobile/v1/clients/1754/",mapOf("business" to "101")),log.last());assertNull(b.client);b.confirmClient(owner,list);assertNull(b.client);search.retryProfile(leaf);runCurrent();b.confirmClient(owner,leaf);assertNull(b.client)
        b.confirmClient(owner,search.control);val proof=b.clientSelection!!;assertEquals(1754,b.client!!.id);assertEquals(raw,proof.rawQuery);assertEquals(s,b.source);assertEquals(7001,b.source!!.clientID);assertNull(search.state.selection);assertEquals("2026-10-29T05:00:00Z",b.rawStart);assertEquals(AppointmentRescheduleResource.Clear,b.resource);assertTrue(b.canReview)
        b.openClientPicker(b.control,search.control);val reopened=b.clientPickerOwner;b.closeClientPicker(owner);b.confirmClient(owner,leaf);assertEquals(reopened,b.clientPickerOwner);assertFalse(b.back(b.control));assertNull(b.clientPickerOwner);assertTrue(b.presented);assertEquals(proof,b.clientSelection)
        b.prepareReview(b.control);assertEquals(proof,b.review!!.input.clientSelection);b.submit(b.control);val retained=b.submission!!.attempt;val body=JSONObject(retained.body);assertEquals(AppointmentBookingPhase.UNKNOWN,b.submission!!.phase);assertEquals(1754,body.getInt("client"));assertEquals(setOf("business","client","service","start_at","resource"),body.keys().asSequence().toSet());b.openClientPicker(b.control,search.control);b.submit(b.control);assertEquals(1,b.retainedAttemptCount);assertEquals(retained,b.submission!!.attempt)
        b.bind(null);b.bind(s.copy(epoch=2));assertTrue(b.blocked);assertFalse(b.canOpen);assertEquals(1,b.retainedAttemptCount)
    }
    @Test fun lateProfileCannotCrossCloseSourceOrActorAndWithheldRetained()=runTest {
        val repo=APIReadRepository(transport());val s=source();val held=CompletableDeferred<ClientProfile>();val searchRepo=object:ClientSearchRepository {
            override suspend fun searchClients(business:Int,search:String)=repo.searchClients(business,search)
            override suspend fun clientProfile(business:Int,id:Int)=held.await()
        }
        val search=ClientSearchModel(searchRepo,this);val b=AppointmentBookingModel(port(),repo,APIAppointmentReferenceRepository(transport()),clientChoices=search);b.bind(s);b.open(b.control);b.openClientPicker(b.control,search.control);val old=b.clientPickerOwner!!;search.submit(search.control);runCurrent();search.openClient(1754,search.control);runCurrent();val leaf=search.control;b.closeClientPicker(old);b.openClientPicker(b.control,search.control);val current=b.clientPickerOwner
        held.complete(repo.clientProfile(101,1754));runCurrent();b.confirmClient(old,leaf);b.closeClientPicker(old);assertEquals(current,b.clientPickerOwner);assertNull(b.client);assertNull(search.profile.state.detail);b.bind(null);b.bind(s);assertNull(search.state.selection);assertNull(b.clientSelection)
        val actorPort=ActorPort(port().grants);val maskedRepo=object:ClientSearchRepository {
            override suspend fun searchClients(business:Int,search:String)=repo.searchClients(business,search)
            override suspend fun clientProfile(business:Int,id:Int):ClientProfile {val o=JSONObject(FixtureClientSearch.profile(fixture("client-search-catalogue-101"),business,id).body);o.getJSONObject("client").put("title",JSONObject.NULL);return JsonContracts.clientProfile(o.toString())}
        }
        val ac=ClientSearchModel(maskedRepo,this);val actor=AppointmentBookingModel(actorPort,repo,APIAppointmentReferenceRepository(transport()),clientChoices=ac);actor.bind(s);actor.open(actor.control);actor.openClientPicker(actor.control,ac.control);val owner=actor.clientPickerOwner!!;ac.submit(ac.control);runCurrent();ac.openClient(1754,ac.control);runCurrent();actorPort.grants=emptyList();actor.confirmClient(owner,ac.control);assertNull(actor.client);actorPort.grants=port().grants;actor.confirmClient(owner,ac.control);assertEquals(1754,actor.client!!.id);assertNull(actor.client!!.title);assertNull(actor.clientSelection!!.choice.title);actor.load(AppointmentBookingReadKind.CLIENT,actor.control);assertEquals(7001,actor.client!!.id);assertNull(actor.clientSelection)
        actor.openClientPicker(actor.control,ac.control);val close=actor.clientPickerOwner;actorPort.grants=emptyList();actor.closeClientPicker(close);assertNull(actor.clientPickerOwner);assertNull(ac.state.selection)
        val none=AppointmentBookingModel(port(),repo,APIAppointmentReferenceRepository(transport()));none.bind(s);none.open(none.control);none.openClientPicker(none.control,null);assertNull(none.clientChoices);assertNull(none.clientPickerOwner)
    }
}
