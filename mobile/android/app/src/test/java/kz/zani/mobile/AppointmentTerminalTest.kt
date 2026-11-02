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
class AppointmentTerminalTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().use {it.readText()}
    private fun source():AppointmentLifecycleSource {val s=AgendaSession();s.install(JsonContracts.bootstrap(fixture("bootstrap.json")));val p=JsonContracts.appointments(fixture("appointments-101.json"));val scope=s.begin(101,p.date);s.receive(p,scope);return AppointmentLifecycleSource(s.beginDetail(501),1,p.items[0])}
    private fun port()=FixtureAppointmentTerminalPort.fromJSON(fixture("appointment-lifecycle.json"),fixture("appointment-terminal.json"))
    private class Held(fixture:FixtureAppointmentTerminalPort):SyntheticAppointmentLifecyclePort {
        override val grants=fixture.grants;override val terminalGrants=fixture.terminalGrants
        val attempts=mutableListOf<AppointmentLifecycleAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticAppointmentLifecycleOutcome>>()
        override suspend fun execute(attempt:AppointmentLifecycleAttempt):SyntheticAppointmentLifecycleOutcome {attempts+=attempt;return CompletableDeferred<SyntheticAppointmentLifecycleOutcome>().also {pending+=it}.await()}
    }
    @Test fun exactGenericPlainReceiptScopeBodyAndFiveActionBarrier()=runTest {
        val commandFixture=port();val s=source();val grant=commandFixture.terminalGrants.first {it.business==101 && it.appointment==501};val mobile=commandFixture.grants.first {it.business==101 && it.appointment==501};val cases=JSONObject(fixture("appointment-terminal.json")).getJSONArray("receipt_cases");val input=AppointmentRescheduleInput.prepare(s,"2026-10-28T05:00:00Z","retained",AppointmentRescheduleResource.Clear)!!
        for(action in listOf(AppointmentLifecycleAction.COMPLETE,AppointmentLifecycleAction.NO_SHOW)) {
            assertNull(mobile.authorization(s,action))
            for(denied in listOf(grant.copy(business=202),grant.copy(appointment=502),grant.copy(actor=0),grant.copy(update=false),grant.copy(actions=emptyList())))assertNull(denied.authorization(s,action))
            for(n in 0 until cases.length()) {
                val row=cases.getJSONObject(n);val ledger=AppointmentLifecycleLedger();val auth=grant.authorization(s,action)!!;val attempt=ledger.begin(AppointmentLifecycleReview(s,action,1),auth)!!
                assertEquals("POST",attempt.method);assertEquals("/api/appointments/501/${action.wire}/",attempt.path);assertEquals(mapOf("business" to "101"),attempt.query);assertEquals(0,JSONObject(attempt.body).length());assertNull(auth.key)
                for(other in AppointmentLifecycleAction.entries) {val a=mobile.authorization(s,other) ?: grant.authorization(s,other)!!;assertNull(ledger.begin(AppointmentLifecycleReview(s,other,2,if(other==AppointmentLifecycleAction.RESCHEDULE)input else null),a))}
                val response=JSONObject(row.getJSONObject("body").toString());if(action==AppointmentLifecycleAction.NO_SHOW && response.opt("status")=="completed")response.put("status","no_show")
                val raw=response.toString();ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.Response(row.getInt("status"),raw));val record=ledger.records[0];val accepted=row.getString("expected")=="acceptedFixture"
                assertEquals(accepted,record.phase==AppointmentLifecyclePhase.ACCEPTED_FIXTURE);assertNull(record.receipt);assertEquals(accepted,record.terminalReceipt!=null)
                if(accepted) {assertEquals(raw,record.terminalReceipt!!.raw);assertTrue(ledger.acknowledge(record));assertTrue(ledger.used(s,action))}else {assertTrue(ledger.blocked(s.copy(epoch=2)));assertFalse(ledger.acknowledge(record));assertEquals(attempt,record.attempt);ledger.complete(attempt,SyntheticAppointmentLifecycleOutcome.Response(200,cases.getJSONObject(0).getJSONObject("body").toString()));assertEquals(AppointmentLifecyclePhase.UNKNOWN,ledger.records[0].phase)}
            }
            val ledger=AppointmentLifecycleLedger();assertNull(ledger.begin(AppointmentLifecycleReview(s,action,1,input),grant.authorization(s,action)!!));val a=ledger.begin(AppointmentLifecycleReview(s,action,2),grant.authorization(s,action)!!)!!;ledger.complete(a,SyntheticAppointmentLifecycleOutcome.RejectedWithoutWrite);assertTrue(ledger.acknowledge(ledger.records[0]));assertFalse(ledger.used(s,action))
        }
    }
    @Test fun explicitReviewBackKnownPlainResultAndMobileContextCannotGrantTerminal()=runTest {
        val s=source();val commandFixture=port();val model=AppointmentLifecycleModel(commandFixture);model.bind(s);val old=model.control!!;model.prepare(AppointmentLifecycleAction.COMPLETE,old);val review=model.control!!
        model.back(old);model.prepare(AppointmentLifecycleAction.NO_SHOW,old);model.submit(old);assertEquals(AppointmentLifecycleAction.COMPLETE,model.review!!.action);assertEquals(0,model.retainedAttemptCount)
        model.back(review);assertNull(model.review);model.prepare(AppointmentLifecycleAction.COMPLETE,old);assertNull(model.review);model.prepare(AppointmentLifecycleAction.COMPLETE,model.control);model.submit(model.control)
        assertEquals("completed",model.submission!!.terminalReceipt!!.status);assertNull(model.submission!!.receipt);assertEquals(s.appointment,model.source!!.appointment);model.acknowledge(model.control,model.submission!!);assertFalse(model.canPrepare(AppointmentLifecycleAction.COMPLETE));assertTrue(model.canPrepare(AppointmentLifecycleAction.NO_SHOW))
        model.prepare(AppointmentLifecycleAction.NO_SHOW,model.control);model.submit(model.control);assertEquals(AppointmentLifecyclePhase.REJECTED_FIXTURE,model.submission!!.phase);model.acknowledge(model.control,model.submission!!);assertTrue(model.canPrepare(AppointmentLifecycleAction.NO_SHOW))
        val mobileOnly=AppointmentLifecycleModel(FixtureAppointmentLifecyclePort.fromJSON(fixture("appointment-lifecycle.json")));mobileOnly.bind(s);assertFalse(mobileOnly.canPrepare(AppointmentLifecycleAction.COMPLETE));assertFalse(mobileOnly.canPrepare(AppointmentLifecycleAction.NO_SHOW))
    }
    @Test fun actualAgendaLateReplyUnknownBusinessRoundTripAndCancellationKeepOriginalRead()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val commandFixture=port();val held=Held(commandFixture)
        val repo=APIReadRepository(ReadTransport {q->val name=when {q.path=="/api/mobile/v1/bootstrap/"->"bootstrap.json";q.path=="/api/mobile/v1/appointments/"->"appointments-${q.query["business"]}.json";else->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}.json"};ReadResponse(200,fixture(name))})
        val m=AgendaViewModel(repo,initialDay={"2026-10-28"},lifecyclePort=held)
        try {
            m.start();runCurrent();m.detail(501);runCurrent();val child=m.lifecycle!!;val original=m.state.detail!!.appointment;val list=m.state.items.map {it.status};m.prepareLifecycle(AppointmentLifecycleAction.COMPLETE,m.lifecycleEntryControl,child.control);val ticket=child.control!!;val pending=async {child.submit(ticket)};runCurrent();child.submit(ticket);for(action in AppointmentLifecycleAction.entries)child.prepare(action,child.control);assertEquals(1,held.attempts.size)
            m.detail(502);runCurrent();held.pending[0].complete(commandFixture.execute(held.attempts[0]));runCurrent();pending.await();assertEquals(502,m.state.detail!!.appointment.id);assertNull(child.submission);assertTrue(child.canPrepare(AppointmentLifecycleAction.NO_SHOW))
            m.detail(501);runCurrent();assertEquals(original.status,m.state.detail!!.appointment.status);assertEquals(list,m.state.items.map {it.status});assertEquals("completed",child.submission!!.terminalReceipt!!.status)
            m.load(202,"2026-10-28");runCurrent();m.detail(601);runCurrent();m.prepareLifecycle(AppointmentLifecycleAction.COMPLETE,m.lifecycleEntryControl,child.control);val unknownControl=child.control!!;val unknown=async {child.submit(unknownControl)};runCurrent();unknown.cancel();runCurrent();held.pending[1].complete(SyntheticAppointmentLifecycleOutcome.Unknown);assertEquals(AppointmentLifecyclePhase.UNKNOWN,child.submission!!.phase);assertNull(child.submission!!.attempt.authorization.key);assertEquals(mapOf("business" to "202"),child.submission!!.attempt.query)
            m.load(101,"2026-10-28");runCurrent();m.detail(502);runCurrent();assertTrue(child.canPrepare(AppointmentLifecycleAction.NO_SHOW));m.load(202,"2026-10-28");runCurrent();m.detail(601);runCurrent();assertTrue(child.blocked);assertNull(child.submission);assertTrue(AppointmentLifecycleAction.entries.all {!child.canPrepare(it)});child.submit(unknownControl);assertEquals(2,held.attempts.size)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
