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
class AppointmentBookingTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().use {it.readText()}
    private fun source():AppointmentBookingSource {val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap.json")));val p=JsonContracts.appointments(fixture("appointments-101.json"));val scope=s.begin(101,p.date);s.receive(p,scope);return AppointmentBookingSource(s.beginDetail(501),1,7001,8001,9001)}
    private fun port()=FixtureAppointmentBookingPort.fromJSON(fixture("appointment-booking.json"))
    private fun client(id:Int=7001)=TaskDraftClientChoice.make(JsonContracts.clientProfile(fixture("client-101-$id.json")),101,id)!!
    private fun service()=AppointmentReferenceDetail.decode(fixture("service-reference-8001.json"),AppointmentReferenceKind.SERVICE)!!
    private fun resource()=AppointmentReferenceDetail.decode(fixture("resource-reference-9001.json"),AppointmentReferenceKind.RESOURCE)!!
    private class HeldPort(override val grants:List<SyntheticAppointmentBookingGrant>):SyntheticAppointmentBookingPort {val attempts=mutableListOf<AppointmentBookingAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticAppointmentBookingOutcome>>();override suspend fun execute(attempt:AppointmentBookingAttempt):SyntheticAppointmentBookingOutcome {attempts+=attempt;return CompletableDeferred<SyntheticAppointmentBookingOutcome>().also {pending+=it}.await()}}
    private class HeldRefs:AppointmentReferenceRepository {val pending=mutableListOf<CompletableDeferred<AppointmentReferenceDetail>>();override suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int)=CompletableDeferred<AppointmentReferenceDetail>().also {pending+=it}.await()}
    private fun transport(calls:MutableList<ReadRequest> = mutableListOf())=ReadTransport {q->calls+=q;val id=q.path.trimEnd('/').substringAfterLast('/');val name=when {
        q.path=="/api/mobile/v1/bootstrap/"->"bootstrap.json"
        q.path=="/api/mobile/v1/appointments/"->"appointments-${q.query["business"]}.json"
        q.path.startsWith("/api/mobile/v1/clients/")->"client-${q.query["business"]}-$id.json"
        q.path.startsWith("/api/services/")->"service-reference-$id.json"
        q.path.startsWith("/api/resources/")->"resource-reference-$id.json"
        else->"appointment-${q.query["business"]}-$id.json"};ReadResponse(200,fixture(name))}
    @Test fun exactFiveFieldsPlain201ChoicesTimesAndUnknownOracles()=runTest {
        val s=source();val c=client();val v=service();val commandFixture=port();val grant=commandFixture.grants.first {it.business==101 && it.fromAppointment==501};val input=AppointmentBookingInput.prepare(s,c,v,AppointmentRescheduleResource.Clear,"2026-10-29T05:00:00Z")!!;val catalog=JSONObject(fixture("appointment-booking.json"));val times=catalog.getJSONArray("time_cases")
        for(n in 0 until times.length()) {val row=times.getJSONObject(n);val value=AppointmentBookingInput.prepare(s,c,v,AppointmentRescheduleResource.Clear,row.getString("raw"));assertEquals(row.getBoolean("valid"),value!=null);value?.let {assertEquals(row.getString("raw"),it.start.raw)}}
        assertNull(AppointmentBookingInput.prepare(s,client(7002),v,AppointmentRescheduleResource.Clear,input.start.raw));assertNull(AppointmentBookingInput.prepare(s,c,v.copy(business=202),AppointmentRescheduleResource.Clear,input.start.raw));assertNull(AppointmentBookingInput.prepare(s.copy(resourceID=null),c,v,AppointmentRescheduleResource.Linked(resource()),input.start.raw))
        for(denied in listOf(grant.copy(business=202),grant.copy(fromAppointment=502),grant.copy(actor=0),grant.copy(create=false)))assertNull(denied.authorization(s))
        val cases=catalog.getJSONArray("receipt_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val ledger=AppointmentBookingLedger();val review=AppointmentBookingReview(s,input,1);val auth=grant.authorization(s)!!;val attempt=ledger.begin(review,auth)!!;val body=JSONObject(attempt.body)
            assertEquals("POST",attempt.method);assertEquals("/api/appointments/",attempt.path);assertTrue(attempt.query.isEmpty());assertEquals(setOf("business","client","service","start_at","resource"),body.keys().asSequence().toSet());assertEquals(101,body.getInt("business"));assertEquals(7001,body.getInt("client"));assertEquals(8001,body.getInt("service"));assertTrue(body.has("resource") && body.isNull("resource"));assertEquals(input.start.raw,body.getString("start_at"));assertNull(ledger.begin(review,auth))
            ledger.complete(attempt,SyntheticAppointmentBookingOutcome.Response(row.getInt("status"),row.getJSONObject("body").toString()));val record=ledger.records[0];val accepted=row.getString("expected")=="acceptedFixture";assertEquals(accepted,record.phase==AppointmentBookingPhase.ACCEPTED_FIXTURE);assertEquals(accepted,record.receipt!=null)
            if(accepted) {assertTrue(ledger.acknowledge(record));assertTrue(ledger.used(s.copy(epoch=2)))}else {assertTrue(ledger.blocked(s.copy(epoch=2)));assertFalse(ledger.acknowledge(record));assertEquals(attempt,record.attempt);ledger.complete(attempt,SyntheticAppointmentBookingOutcome.Response(201,cases.getJSONObject(0).getJSONObject("body").toString()));assertEquals(AppointmentBookingPhase.UNKNOWN,ledger.records[0].phase)}
        }
        val ledger=AppointmentBookingLedger();val a=ledger.begin(AppointmentBookingReview(s,input,1),grant.authorization(s)!!)!!;ledger.complete(a,commandFixture.execute(a));assertEquals(AppointmentBookingPhase.ACCEPTED_FIXTURE,ledger.records[0].phase)
        val rejected=AppointmentBookingLedger();val r=rejected.begin(AppointmentBookingReview(s,input,1),grant.authorization(s)!!)!!;rejected.complete(r,SyntheticAppointmentBookingOutcome.RejectedWithoutWrite);assertTrue(rejected.acknowledge(rejected.records[0]));assertFalse(rejected.used(s))
        val linked=AppointmentBookingInput.prepare(s,c,v,AppointmentRescheduleResource.Linked(resource()),input.start.raw)!!;assertEquals(9001,JSONObject(linked.body(101)!!).getInt("resource"))
    }
    @Test fun stableInputsExplicitScopedReadsReviewBackLateAndDeniedChoices()=runTest {
        val calls=mutableListOf<ReadRequest>();val read=transport(calls);val repo=APIReadRepository(read);val refs=APIAppointmentReferenceRepository(read);val model=AppointmentBookingModel(port(),repo,refs);model.bind(source());model.open(model.control);assertEquals("",model.rawStart);assertNull(model.client);assertNull(model.service);assertNull(model.resource);assertFalse(model.canReview)
        val input=model.inputControl!!;val old=model.control!!;model.setStart("2026-10-29T05:00:00",input);model.setStart("2026-10-29T05:00:00Z",input);model.chooseClear(old);assertNull(model.resource);assertFalse(model.canReview)
        model.load(AppointmentBookingReadKind.CLIENT,model.control);model.load(AppointmentBookingReadKind.SERVICE,model.control);model.load(AppointmentBookingReadKind.RESOURCE,model.control);assertEquals(7001,model.client!!.id);assertEquals(8001,model.service!!.id);assertEquals(9001,model.resource!!.id)
        assertTrue(ReadRequest("/api/mobile/v1/clients/7001/",mapOf("business" to "101")) in calls);assertTrue(ReadRequest("/api/services/8001/") in calls);assertTrue(ReadRequest("/api/resources/9001/") in calls)
        model.chooseClear(model.control);model.prepareReview(model.control);val review=model.review!!;model.setStart("stale",input);assertFalse(model.back(model.control));assertEquals(review.input.start.raw,model.rawStart);assertEquals(review.input.client,model.client);assertEquals(review.input.service,model.service);assertTrue(model.back(model.control));assertEquals(review.input.start.raw,model.rawStart);model.open(model.control);model.setStart("stale",input);assertEquals(review.input.start.raw,model.rawStart)
        val heldRefs=HeldRefs();val late=AppointmentBookingModel(port(),repo,heldRefs);late.bind(source());late.open(late.control);late.setStart("2026-10-29T05:00:00Z",late.inputControl);val pending=async {late.load(AppointmentBookingReadKind.SERVICE,late.control)};runCurrent();late.back(late.control);late.open(late.control);heldRefs.pending[0].complete(service());runCurrent();pending.await();assertNull(late.service);assertNull(late.loading);assertEquals("2026-10-29T05:00:00Z",late.rawStart)
        val denied=async {late.load(AppointmentBookingReadKind.SERVICE,late.control)};runCurrent();heldRefs.pending[1].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();denied.await();assertEquals(ReadProblem.DENIED,late.failure);assertNull(late.service);assertFalse(late.canReview);assertEquals("2026-10-29T05:00:00Z",late.rawStart)
    }
    @Test fun actualAgendaKnownResultDoesNotMutateGETAndUnknownRetainsAcrossBusinessRereadCancellation()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val read=transport();val repo=APIReadRepository(read);val refs=APIAppointmentReferenceRepository(read);val commandFixture=port();val held=HeldPort(commandFixture.grants);val m=AgendaViewModel(repo,initialDay={"2026-10-28"},bookingPort=held,bookingClients=repo,bookingReferences=refs)
        try {
            m.start();runCurrent();m.detail(501);runCurrent();val child=m.booking!!;val original=m.state.detail!!.appointment;val ids=m.state.items.map {it.id};val entry=m.bookingEntryControl!!;val oldParent=m.control;m.openBooking(entry,child.control);val input=child.inputControl!!;child.setStart("2026-10-29T05:00:00Z",input);child.load(AppointmentBookingReadKind.CLIENT,child.control);child.load(AppointmentBookingReadKind.SERVICE,child.control);child.chooseClear(child.control);child.prepareReview(child.control);m.back(oldParent);assertEquals(501,m.state.detail!!.appointment.id)
            val ticket=child.control!!;val pending=async {child.submit(ticket)};runCurrent();child.submit(ticket);m.backBooking(m.bookingEntryControl,child.control);assertEquals(1,held.attempts.size);held.pending[0].complete(commandFixture.execute(held.attempts[0]));runCurrent();pending.await();assertEquals(AppointmentBookingPhase.ACCEPTED_FIXTURE,child.submission!!.phase);assertEquals(1501,child.submission!!.receipt!!.appointment.id);assertEquals(original,m.state.detail!!.appointment);assertEquals(ids,m.state.items.map {it.id});m.acknowledgeBooking(m.bookingEntryControl,child.control,child.submission!!);assertFalse(child.canOpen)
            m.detail(502);runCurrent();m.openBooking(entry,child.control);assertFalse(child.presented);m.openBooking(m.bookingEntryControl,child.control);child.setStart("2026-10-29T05:00:00Z",child.inputControl);child.load(AppointmentBookingReadKind.CLIENT,child.control);child.load(AppointmentBookingReadKind.SERVICE,child.control);child.chooseClear(child.control);child.prepareReview(child.control);val unknownControl=child.control!!;val unknown=async {child.submit(unknownControl)};runCurrent();m.detail(501);runCurrent();held.pending[1].complete(SyntheticAppointmentBookingOutcome.Unknown);runCurrent();unknown.await();assertEquals(501,m.state.detail!!.appointment.id);assertNull(child.submission)
            m.load(202,"2026-10-28");runCurrent();m.detail(601);runCurrent();m.openBooking(m.bookingEntryControl,child.control);child.setStart("2026-10-29T05:00:00Z",child.inputControl);child.load(AppointmentBookingReadKind.SERVICE,child.control);assertEquals(ReadProblem.INVALID_PAYLOAD,child.failure);assertNull(child.service);assertEquals("2026-10-29T05:00:00Z",child.rawStart)
            m.load(101,"2026-10-28");runCurrent();m.detail(502);runCurrent();assertTrue(child.blocked);assertNull(child.submission);assertFalse(child.canOpen);child.submit(unknownControl);assertEquals(2,held.attempts.size);assertEquals("2026-10-29T05:00:00Z",held.attempts[1].review.input.start.raw)
            // Independent new model: cancellation maps a late valid201 to unknown, retaining attempt.
            val cancelPort=HeldPort(commandFixture.grants);val cancelled=AppointmentBookingModel(cancelPort,repo,refs);cancelled.bind(source());cancelled.open(cancelled.control);cancelled.setStart("2026-10-29T05:00:00Z",cancelled.inputControl);cancelled.load(AppointmentBookingReadKind.CLIENT,cancelled.control);cancelled.load(AppointmentBookingReadKind.SERVICE,cancelled.control);cancelled.chooseClear(cancelled.control);cancelled.prepareReview(cancelled.control);val cancel=async {cancelled.submit(cancelled.control)};runCurrent();cancel.cancel();runCurrent();cancelPort.pending[0].complete(commandFixture.execute(cancelPort.attempts[0]));assertEquals(AppointmentBookingPhase.UNKNOWN,cancelled.submission!!.phase);assertEquals(cancelPort.attempts[0],cancelled.submission!!.attempt)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
