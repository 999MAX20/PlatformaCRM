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
class AppointmentRescheduleTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().use {it.readText()}
    private fun source():AppointmentLifecycleSource {val session=AgendaSession();session.install(JsonContracts.bootstrap(fixture("bootstrap.json")));val p=JsonContracts.appointments(fixture("appointments-101.json"));val scope=session.begin(101,p.date);session.receive(p,scope);return AppointmentLifecycleSource(session.beginDetail(501),1,p.items[0],9001)}
    private fun port()=FixtureAppointmentLifecyclePort.fromJSON(fixture("appointment-lifecycle.json"))
    private class HeldRefs:AppointmentReferenceRepository {val pending=mutableListOf<CompletableDeferred<AppointmentReferenceDetail>>();override suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int)=CompletableDeferred<AppointmentReferenceDetail>().also {pending+=it}.await()}
    private class HeldPort(override val grants:List<SyntheticAppointmentLifecycleGrant>):SyntheticAppointmentLifecyclePort {val attempts=mutableListOf<AppointmentLifecycleAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticAppointmentLifecycleOutcome>>();override suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome {attempts+=attempt;return CompletableDeferred<SyntheticAppointmentLifecycleOutcome>().also {pending+=it}.await()}}
    @Test fun sharedExplicitTimeBodyResourceAndBoundedReceiptOracles()=runTest {
        val catalog=JSONObject(fixture("appointment-reschedule.json"));val s=source();val grant=port().grants.first {it.business==101 && it.appointment==501};val raw=catalog.getJSONObject("inputs").getJSONObject("501");val start=raw.getString("start_at");val reason=raw.getString("reason_raw");val times=catalog.getJSONArray("time_cases")
        for(n in 0 until times.length()) {val row=times.getJSONObject(n);val value=AppointmentRescheduleInput.prepare(s,row.getString("raw"),reason,AppointmentRescheduleResource.Clear);assertEquals(row.getBoolean("valid"),value!=null);value?.let {assertEquals(row.getString("raw"),it.start.raw);assertEquals(reason,it.rawReason);assertEquals(reason.trim(),it.reason)}}
        val resource=AppointmentReferenceDetail.decode(fixture("resource-reference-9001.json"),AppointmentReferenceKind.RESOURCE)!!;assertNotNull(AppointmentRescheduleInput.prepare(s,start,reason,AppointmentRescheduleResource.Linked(resource)));assertNull(AppointmentRescheduleInput.prepare(s,start,reason,AppointmentRescheduleResource.Linked(resource.copy(business=202))));assertNull(AppointmentRescheduleInput.prepare(s.copy(linkedResourceID=null),start,reason,AppointmentRescheduleResource.Linked(resource)))
        for(status in listOf("cancelled","completed","no_show"))assertNull(AppointmentRescheduleInput.prepare(s.copy(appointment=s.appointment.copy(status=status)),start,reason,AppointmentRescheduleResource.Clear))
        val input=AppointmentRescheduleInput.prepare(s,start,reason,AppointmentRescheduleResource.Clear)!!;val cases=catalog.getJSONArray("receipt_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val ledger=AppointmentLifecycleLedger();val attempt=ledger.begin(AppointmentLifecycleReview(s,AppointmentLifecycleAction.RESCHEDULE,1,input),grant.authorization(s,AppointmentLifecycleAction.RESCHEDULE)!!)!!;val body=JSONObject(attempt.body)
            assertEquals(setOf("business","start_at","resource","reason"),body.keys().asSequence().toSet());assertTrue(body.has("resource") && body.isNull("resource"));assertEquals(101,body.getInt("business"));assertEquals(start,body.getString("start_at"));assertEquals(input.reason,body.getString("reason"));assertEquals(grant.rescheduleKey,attempt.authorization.key);assertEquals("/api/mobile/v1/appointments/501/reschedule/",attempt.path)
            for(a in AppointmentLifecycleAction.entries)assertNull(ledger.begin(AppointmentLifecycleReview(s,a,2,if(a==AppointmentLifecycleAction.RESCHEDULE)input else null),(grant.authorization(s,a) ?: SyntheticAppointmentTerminalGrant(101,501,5001,true,listOf(AppointmentLifecycleAction.COMPLETE,AppointmentLifecycleAction.NO_SHOW)).authorization(s,a))!!))
            ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.Response(row.getInt("status"),row.getJSONObject("body").toString()));val record=ledger.records[0];assertEquals(row.getString("expected"),if(record.phase==AppointmentLifecyclePhase.ACCEPTED_FIXTURE)"acceptedFixture" else "unknown")
            if(record.phase==AppointmentLifecyclePhase.UNKNOWN) {assertFalse(ledger.acknowledge(record));assertEquals(input,record.attempt.review.reschedule);assertEquals(attempt.body,record.attempt.body);assertTrue(ledger.blocked(s))}else {assertTrue(ledger.acknowledge(record));assertTrue(ledger.used(s,AppointmentLifecycleAction.RESCHEDULE))}
        }
    }
    @Test fun stableInputReviewBackAndScopedResourceReadRetainOriginalGET()=runTest {
        val s=source();val calls=mutableListOf<ReadRequest>();val refs=APIAppointmentReferenceRepository(ReadTransport {q->calls+=q;ReadResponse(200,fixture("resource-reference-9001.json"))});val model=AppointmentLifecycleModel(port(),refs);model.bind(s);model.prepare(AppointmentLifecycleAction.RESCHEDULE,model.control)
        assertEquals("",model.rawStart);assertEquals("",model.rawReason);assertNull(model.resourceChoice);assertFalse(model.canReviewReschedule)
        val input=model.inputControl!!;val old=model.control!!;model.setStart("2026-10-28T05:00:00",input);model.setStart("2026-10-28T05:00:00Z",input);model.setReason("é",input);model.setReason("  Synthetic move e\u0301  ",input)
        assertTrue(model.timeInputValid);assertEquals("  Synthetic move e\u0301  ",model.rawReason);model.chooseClear(old);assertNull(model.resourceChoice);model.chooseClear(model.control);model.reviewReschedule(model.control);val review=model.review!!
        model.setReason("stale",input);model.back(model.control);assertEquals(review.reschedule!!.rawReason,model.rawReason);model.setStart("stale",input);assertEquals("2026-10-28T05:00:00Z",model.rawStart)
        model.loadLinkedResource(model.control);assertEquals(9001,model.resourceChoice!!.id);assertEquals(listOf(ReadRequest("/api/resources/9001/")),calls)
        model.chooseClear(model.control);model.reviewReschedule(model.control);model.submit(model.control);assertEquals(AppointmentLifecyclePhase.ACCEPTED_FIXTURE,model.submission!!.phase);assertEquals(s.appointment.startAt,model.source!!.appointment.startAt);model.acknowledge(model.control,model.submission!!);assertTrue(model.used(AppointmentLifecycleAction.RESCHEDULE));assertFalse(model.canPrepare(AppointmentLifecycleAction.RESCHEDULE));assertTrue(model.canPrepare(AppointmentLifecycleAction.CANCEL))
    }
    @Test fun actualAgendaLateResourceFailureAndUnknownAcrossTargetsBusinessDoNotRestoreOrReplay()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val refs=HeldRefs();val commandFixture=port();val port=HeldPort(commandFixture.grants)
        val repo=APIReadRepository(ReadTransport {q->val name=when {q.path=="/api/mobile/v1/bootstrap/"->"bootstrap.json";q.path=="/api/mobile/v1/appointments/"->"appointments-${q.query["business"]}.json";else->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}.json"};ReadResponse(200,fixture(name))})
        val m=AgendaViewModel(repo,initialDay={"2026-10-28"},lifecyclePort=port,lifecycleReferences=refs)
        try {
            m.start();runCurrent();m.detail(501);runCurrent();val child=m.lifecycle!!;m.prepareLifecycle(AppointmentLifecycleAction.RESCHEDULE,m.lifecycleEntryControl,child.control);val input=child.inputControl!!;child.setStart("2026-10-28T05:00:00Z",input);child.setReason("  retained e\u0301  ",input)
            val first=async {child.loadLinkedResource(child.control)};runCurrent();child.back(child.control);m.prepareLifecycle(AppointmentLifecycleAction.RESCHEDULE,m.lifecycleEntryControl,child.control);val resource=AppointmentReferenceDetail.decode(fixture("resource-reference-9001.json"),AppointmentReferenceKind.RESOURCE)!!;refs.pending[0].complete(resource);runCurrent();first.await();assertNull(child.resourceChoice);assertFalse(child.resourceLoading);assertEquals("2026-10-28T05:00:00Z",child.rawStart);assertEquals("  retained e\u0301  ",child.rawReason)
            val denied=async {child.loadLinkedResource(child.control)};runCurrent();refs.pending[1].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();denied.await();assertEquals(ReadProblem.DENIED,child.resourceFailure);assertNull(child.resourceChoice);assertFalse(child.canReviewReschedule);assertEquals("2026-10-28T05:00:00Z",child.rawStart)
            child.chooseClear(child.control);child.reviewReschedule(child.control);val reviewed=child.control!!;val pending=async {child.submit(reviewed)};runCurrent();for(a in AppointmentLifecycleAction.entries)child.prepare(a,child.control);child.setReason("lost",input);assertTrue(child.blocked);assertEquals(1,child.retainedAttemptCount)
            m.detail(502);runCurrent();port.pending[0].complete(SyntheticAppointmentLifecycleOutcome.Unknown);runCurrent();pending.await();assertEquals(502,m.state.detail!!.appointment.id);assertNull(child.submission);assertTrue(child.canPrepare(AppointmentLifecycleAction.RESCHEDULE))
            m.load(202,"2026-10-28");runCurrent();m.load(101,"2026-10-28");runCurrent();m.detail(501);runCurrent();assertTrue(child.blocked);assertNull(child.submission);assertTrue(AppointmentLifecycleAction.entries.all {!child.canPrepare(it)});assertEquals(1,child.retainedAttemptCount)
            val attempt=port.attempts[0];assertEquals("  retained e\u0301  ",attempt.review.reschedule!!.rawReason);assertEquals("retained e\u0301",JSONObject(attempt.body).getString("reason"));assertTrue(JSONObject(attempt.body).isNull("resource"))
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
