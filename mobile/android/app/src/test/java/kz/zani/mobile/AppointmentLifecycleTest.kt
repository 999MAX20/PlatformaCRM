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
class AppointmentLifecycleTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().use {it.readText()}
    private fun source(business:Int=101,id:Int=501):AppointmentLifecycleSource {
        val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap.json")));val page=JsonContracts.appointments(fixture("appointments-$business.json"));val scope=s.begin(business,page.date);s.receive(page,scope);return AppointmentLifecycleSource(s.beginDetail(id),1,page.items.first {it.id==id})
    }
    private class Held(override val grants:List<SyntheticAppointmentLifecycleGrant>):SyntheticAppointmentLifecyclePort {
        val attempts=mutableListOf<AppointmentLifecycleAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticAppointmentLifecycleOutcome>>()
        override suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome {attempts+=attempt;return CompletableDeferred<SyntheticAppointmentLifecycleOutcome>().also {pending+=it}.await()}
    }
    @Test fun exactReceiptCasesBodyProvidedKeysAndCrossActionBarrier()=runTest {
        val catalog=JSONObject(fixture("appointment-lifecycle.json"));val port=FixtureAppointmentLifecyclePort.fromJSON(catalog.toString());val source=source();val grant=port.grants.first {it.business==101 && it.appointment==501};val cases=catalog.getJSONArray("receipt_cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val ledger=AppointmentLifecycleLedger();val a=grant.authorization(source,AppointmentLifecycleAction.CONFIRM)!!;val attempt=ledger.begin(AppointmentLifecycleReview(source,AppointmentLifecycleAction.CONFIRM,1),a)!!
            val body=JSONObject(attempt.body);assertEquals(setOf("business"),body.keys().asSequence().toSet());assertEquals(101,body.getInt("business"));assertEquals(grant.confirmKey,attempt.authorization.key);assertEquals("/api/mobile/v1/appointments/501/confirm/",attempt.path)
            assertNull(ledger.begin(AppointmentLifecycleReview(source,AppointmentLifecycleAction.CANCEL,2),grant.authorization(source,AppointmentLifecycleAction.CANCEL)!!))
            ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.Response(row.getInt("status"),row.getJSONObject("body").toString()));val record=ledger.records[0];assertEquals(row.getString("expected"),if(record.phase==AppointmentLifecyclePhase.ACCEPTED_FIXTURE)"acceptedFixture" else "unknown");assertEquals(row.getString("expected")=="acceptedFixture",record.receipt!=null)
            if(record.phase==AppointmentLifecyclePhase.UNKNOWN) {ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.Response(200,cases.getJSONObject(0).getJSONObject("body").toString()));assertEquals(AppointmentLifecyclePhase.UNKNOWN,ledger.records[0].phase);assertFalse(ledger.acknowledge(record));assertTrue(ledger.blocked(source));assertEquals(attempt.body,ledger.records[0].attempt.body)}
            else {assertTrue(ledger.acknowledge(record));assertTrue(ledger.used(source,AppointmentLifecycleAction.CONFIRM));assertFalse(ledger.blocked(source))}
        }
    }
    @Test fun explicitSyntheticAuthorityRejectionAndOpaqueRawKeyIdentity()=runTest {
        val s=source();val good=SyntheticAppointmentLifecycleGrant(101,501,5001,true,"e\u0301","cancel-key")
        val different=SyntheticAppointmentLifecycleGrant(101,501,5001,true,"é","cancel-key");assertNotEquals(good,different);assertNotEquals(good.authorization(s,AppointmentLifecycleAction.CONFIRM),different.authorization(s,AppointmentLifecycleAction.CONFIRM))
        for(a in AppointmentLifecycleAction.entries)for(g in listOf(good.copy(business=202),good.copy(appointment=502),good.copy(actor=0),good.copy(update=false),good.copy(confirmKey=" \t",cancelKey=null)))assertNull(g.authorization(s,a))
        val ledger=AppointmentLifecycleLedger();val a=good.authorization(s,AppointmentLifecycleAction.CANCEL)!!;val attempt=ledger.begin(AppointmentLifecycleReview(s,AppointmentLifecycleAction.CANCEL,1),a)!!;ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.RejectedWithoutWrite);val record=ledger.records[0];assertEquals(AppointmentLifecyclePhase.REJECTED_FIXTURE,record.phase);assertTrue(ledger.acknowledge(record));assertFalse(ledger.used(s,AppointmentLifecycleAction.CANCEL))
        val ambiguous=AppointmentLifecycleModel(object:SyntheticAppointmentLifecyclePort {override val grants=listOf(good,different);override suspend fun execute(attempt:AppointmentLifecycleAttempt)=SyntheticAppointmentLifecycleOutcome.Unknown});ambiguous.bind(s);assertFalse(ambiguous.canPrepare(AppointmentLifecycleAction.CONFIRM))
    }
    @Test fun actualAgendaParentLateTargetUnknownBusinessAndCancellationKeepOriginalReads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=APIReadRepository(ReadTransport {q->val name=when {q.path=="/api/mobile/v1/bootstrap/"->"bootstrap.json";q.path=="/api/mobile/v1/appointments/"->"appointments-${q.query["business"]}.json";q.path.startsWith("/api/mobile/v1/appointments/")->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}.json";else->null};if(name==null)ReadResponse(404,"")else ReadResponse(200,fixture(name))});val fixturePort=FixtureAppointmentLifecyclePort.fromJSON(fixture("appointment-lifecycle.json"));val port=Held(fixturePort.grants);val links=AppointmentRelationsViewModel(repo)
        val baseline=AgendaViewModel(repo,initialDay={"2026-10-28"});val m=AgendaViewModel(repo,initialDay={"2026-10-28"},relations=links,lifecyclePort=port)
        try {
            baseline.start();runCurrent();baseline.detail(501);runCurrent();assertNull(baseline.lifecycle);assertNull(baseline.lifecycleEntryControl)
            m.start();runCurrent();m.detail(501);runCurrent();val child=m.lifecycle!!;val entry=m.lifecycleEntryControl!!;val old=child.control!!;val original=m.state.detail!!;val statuses=m.state.items.map {it.status}
            links.openClient(links.presentation);runCurrent();links.back(links.presentation);m.prepareLifecycle(AppointmentLifecycleAction.CONFIRM,entry,old);assertNull(child.review)
            m.prepareLifecycle(AppointmentLifecycleAction.CONFIRM,m.lifecycleEntryControl,old);val review=child.control!!;child.back(old);child.prepare(AppointmentLifecycleAction.CANCEL,old);child.submit(old);assertEquals(AppointmentLifecycleAction.CONFIRM,child.review!!.action);assertEquals(0,child.retainedAttemptCount)
            val first=async {child.submit(review)};runCurrent();child.submit(review);child.prepare(AppointmentLifecycleAction.CANCEL,child.control);assertEquals(1,port.attempts.size);assertTrue(child.blocked)
            val parent=m.control;m.detail(502);runCurrent();m.back(parent);port.pending[0].complete(fixturePort.execute(port.attempts[0]));runCurrent();first.await();assertEquals(502,m.state.detailID);assertEquals("created",m.state.detail!!.appointment.status);assertNull(child.submission);assertEquals(statuses,m.state.items.map {it.status})
            m.detail(501);runCurrent();assertEquals(original.appointment.status,m.state.detail!!.appointment.status);assertEquals(AppointmentLifecyclePhase.ACCEPTED_FIXTURE,child.submission!!.phase);child.acknowledge(child.control,child.submission!!);assertTrue(child.used(AppointmentLifecycleAction.CONFIRM));assertFalse(child.canPrepare(AppointmentLifecycleAction.CONFIRM));assertTrue(child.canPrepare(AppointmentLifecycleAction.CANCEL))
            m.prepareLifecycle(AppointmentLifecycleAction.CANCEL,m.lifecycleEntryControl,child.control);val cancelControl=child.control!!;val unknown=async {child.submit(cancelControl)};runCurrent();m.back();m.load(202,"2026-10-28");runCurrent();m.detail(601);runCurrent();port.pending[1].complete(SyntheticAppointmentLifecycleOutcome.Unknown);runCurrent();unknown.await();assertEquals(202,m.state.selection!!.business.id);assertEquals(601,m.state.detail!!.appointment.id);assertNull(child.submission);assertEquals(2,child.retainedAttemptCount)
            m.load(101,"2026-10-28");runCurrent();m.detail(501);runCurrent();assertTrue(child.blocked);assertNull(child.submission);assertFalse(child.canPrepare(AppointmentLifecycleAction.CONFIRM));assertFalse(child.canPrepare(AppointmentLifecycleAction.CANCEL));m.prepareLifecycle(AppointmentLifecycleAction.CONFIRM,entry,old);child.submit(cancelControl);assertEquals(2,port.attempts.size)
            m.detail(502);runCurrent();assertTrue(child.canPrepare(AppointmentLifecycleAction.CANCEL))
            m.load(202,"2026-10-28");runCurrent();m.detail(601);runCurrent();m.prepareLifecycle(AppointmentLifecycleAction.CONFIRM,m.lifecycleEntryControl,child.control);val held=child.control!!;val cancelled=async {child.submit(held)};runCurrent();cancelled.cancel();runCurrent();assertEquals(AppointmentLifecyclePhase.UNKNOWN,child.submission!!.phase);assertEquals(3,child.retainedAttemptCount);port.pending[2].complete(fixturePort.execute(port.attempts[2]));runCurrent();assertTrue(cancelled.isCancelled)
        } finally {baseline.viewModelScope.cancel();m.viewModelScope.cancel();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
