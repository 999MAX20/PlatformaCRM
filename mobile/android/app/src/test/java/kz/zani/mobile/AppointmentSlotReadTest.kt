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
class AppointmentSlotReadTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun service()=AppointmentReferenceDetail.decode(fixture("service-reference-8001"),AppointmentReferenceKind.SERVICE)!!
    private fun resource(id:Int=9001)=AppointmentReferenceDetail.decode(fixture("resource-reference-$id"),AppointmentReferenceKind.RESOURCE)!!
    private class Slots:AppointmentSlotRepository {
        val calls=mutableListOf<AppointmentSlotIntent>();val pending=mutableListOf<CompletableDeferred<AppointmentSlotRead>>()
        override suspend fun slots(intent:AppointmentSlotIntent):AppointmentSlotRead {calls+=intent;return CompletableDeferred<AppointmentSlotRead>().also {pending+=it}.await()}
    }
    private class References:AppointmentReferenceRepository {
        val calls=mutableListOf<Triple<AppointmentReferenceKind,Int,Int>>();val pending=mutableListOf<CompletableDeferred<AppointmentReferenceDetail>>()
        override suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int):AppointmentReferenceDetail {calls+=Triple(kind,business,id);return CompletableDeferred<AppointmentReferenceDetail>().also {pending+=it}.await()}
    }
    private fun check(block:suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,AppointmentSlotReadViewModel,Slots,References)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val slots=Slots();val references=References()
        val transport=ReadTransport {q->val name=when {q.path.endsWith("/bootstrap/")->"bootstrap";q.path.endsWith("/appointments/")->"appointments-${q.query["business"]}";else->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}"};ReadResponse(200,fixture(name))}
        val repository=APIReadRepository(transport);val refRepo=APIAppointmentReferenceRepository(ReadTransport {q->ReadResponse(200,fixture("${if(q.path.contains("/services/"))"service" else "resource"}-reference-${q.path.trimEnd('/').substringAfterLast('/')}"))});val links=AppointmentRelationsViewModel(repository,refRepo,slots);val parent=AgendaViewModel(repository,initialDay={"2026-10-28"},relations=links)
        var model:AppointmentSlotReadViewModel?=null
        try {
            parent.start();runCurrent();parent.openDetail(501,parent.control);runCurrent();links.openReference(AppointmentReferenceKind.SERVICE,links.presentation);runCurrent()
            val child=AppointmentSlotReadViewModel(slots,references);model=child;child.bind(links.state.reference!!,links.state.request!!,9001)
            block(parent,links,child,slots,references)
        }finally {model?.clear();model?.viewModelScope?.cancel();links.clear();links.slotReads.viewModelScope.cancel();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private fun ready(model:AppointmentSlotReadViewModel,mode:AppointmentSlotResourceMode=AppointmentSlotResourceMode.UNSPECIFIED) {model.open(model.presentation);model.setDay("2026-11-02",model.presentation);model.choose(mode,model.presentation)}
    @Test fun sharedDirectArrayStatusAndExplicitOffsetCases()=runTest {
        val rows=JSONObject(fixture("appointment-slot-read-cases")).getJSONArray("cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val intent=AppointmentSlotIntent.make(Business(101,"Synthetic",row.getString("timezone")),service(),null,row.getString("day"))!!;val calls=mutableListOf<ReadRequest>();val repository=APIAppointmentSlotRepository(ReadTransport {q->calls+=q;ReadResponse(row.getInt("status"),row.getString("response_json"))});var result:AppointmentSlotRead?=null;var problem:ReadProblem?=null
            try {result=repository.slots(intent)}catch(e:ReadException){problem=e.problem}
            assertEquals(row.getString("name"),row.getBoolean("valid"),result!=null);assertEquals(listOf(ReadRequest("/api/appointments/available-slots/",mapOf("business_id" to "101","service_id" to "8001","date" to row.getString("day")))),calls)
            if(result!=null){assertTrue(result.validFor(intent));val array=row.getJSONArray("response");assertEquals(array.length(),result.candidates.size);result.candidates.forEachIndexed {j,value->assertEquals(array.getJSONObject(j).getString("start_at"),value.startAt);assertEquals(array.getJSONObject(j).getString("end_at"),value.endAt)}}
            else assertEquals(when(row.getInt("status")){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;200->ReadProblem.INVALID_PAYLOAD;else->ReadProblem.UNAVAILABLE},problem)
        }
    }
    @Test fun explicitDayAndIndependentIdentityAreRequired() {
        val rows=JSONObject(fixture("appointment-slot-read-cases")).getJSONArray("intent_cases");val business=Business(101,"Synthetic","Asia/Almaty")
        for(i in 0 until rows.length()){val row=rows.getJSONObject(i);assertEquals(row.getBoolean("valid"),AppointmentSlotIntent.make(business,service(),null,row.getString("day"))!=null)}
        assertNull(AppointmentSlotIntent.make(business.copy(timezone="Unknown/Zone"),service(),null,"2026-11-02"));assertNull(AppointmentSlotIntent.make(business.copy(id=202),service(),null,"2026-11-02"));assertNull(AppointmentSlotIntent.make(business,service(),resource(9002),"2026-11-02"))
        assertEquals(mapOf("business_id" to "101","service_id" to "8001","resource_id" to "9001","date" to "2026-11-02"),AppointmentSlotIntent.make(business,service(),resource(),"2026-11-02")!!.query)
    }
    @Test fun emptyFormDoesNotDefaultAgendaDateOrResource()=check {_,_,m,p,_->
        m.open(m.presentation);assertEquals("",m.state.day);assertNull(m.state.resourceMode);assertFalse(m.canRead);m.submit(m.presentation);runCurrent();assertTrue(p.calls.isEmpty());m.setDay("2026-11-02",m.presentation);assertFalse(m.canRead);m.submit(m.presentation);runCurrent();assertTrue(p.calls.isEmpty())
    }
    @Test fun pendingInputDuplicateRetryAndOldBackCannotReplaceIntent()=check {_,_,m,p,_->
        ready(m);val before=m.presentation;m.submit(before);runCurrent();val pending=m.presentation;m.setDay("2026-11-03",pending);m.choose(AppointmentSlotResourceMode.LINKED,pending);m.retry(pending);m.submit(pending);m.close(before);runCurrent();assertEquals(1,p.calls.size);assertEquals("2026-11-02",m.state.day);assertEquals(AppointmentSlotResourceMode.UNSPECIFIED,m.state.resourceMode);assertTrue(m.state.loading);p.pending[0].complete(AppointmentSlotRead(p.calls[0],emptyList()));runCurrent()
    }
    @Test fun denialRetainsInputAndRetryUsesFreshControl()=check {_,_,m,p,_->
        ready(m);m.submit(m.presentation);runCurrent();val old=m.presentation;p.pending[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,m.state.problem);assertNull(m.state.read);assertEquals("2026-11-02",m.state.day);m.retry(m.presentation);runCurrent();val current=m.presentation;m.close(old);m.edit(old);runCurrent();assertEquals(2,p.calls.size);assertEquals(p.calls[0],p.calls[1]);p.pending[1].complete(AppointmentSlotRead(p.calls[1],emptyList()));runCurrent();assertEquals(current,m.presentation);assertTrue(m.state.read!!.candidates.isEmpty());assertNull(m.state.problem)
    }
    @Test fun lateResponseCannotReplaceReopenedExplicitInput()=check {_,_,m,p,_->
        ready(m);m.submit(m.presentation);runCurrent();val old=m.presentation;m.close(old);ready(m);m.setDay("2026-11-03",m.presentation);val current=m.presentation;p.pending[0].complete(AppointmentSlotRead(p.calls[0],emptyList()));runCurrent();m.setDay("2026-11-02",old);m.submit(old);runCurrent();assertEquals(current,m.presentation);assertEquals("2026-11-03",m.state.day);assertNull(m.state.read);assertEquals(1,p.calls.size)
    }
    @Test fun linkedResourceIsReadAndScopeValidatedBeforeSlotGet()=check {_,_,m,p,r->
        ready(m,AppointmentSlotResourceMode.LINKED);m.submit(m.presentation);runCurrent();assertTrue(p.calls.isEmpty());assertEquals(Triple(AppointmentReferenceKind.RESOURCE,101,9001),r.calls.single());r.pending[0].complete(resource());runCurrent();assertEquals(9001,p.calls.single().resource);assertFalse(p.calls.single().query.containsKey("exclude_appointment_id"));p.pending[0].complete(AppointmentSlotRead(p.calls[0],emptyList()));runCurrent()
    }
    @Test fun foreignResourceCannotReachCandidatePort()=check {_,_,m,p,r->
        ready(m,AppointmentSlotResourceMode.LINKED);m.submit(m.presentation);runCurrent();r.pending[0].complete(resource(9002));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,m.state.problem);assertTrue(p.calls.isEmpty());assertEquals("2026-11-02",m.state.day)
    }
    @Test fun closeDuringReferenceLookupCannotStartLateCandidateRead()=check {_,_,m,p,r->
        ready(m,AppointmentSlotResourceMode.LINKED);m.submit(m.presentation);runCurrent();m.close(m.presentation);r.pending[0].complete(resource());runCurrent();assertFalse(m.state.presented);assertNull(m.state.read);assertTrue(p.calls.isEmpty())
    }
    @Test fun parentRefreshClearsIntegratedSlotOwnerAndLateResult()=check {parent,links,_,p,_->
        val m=links.slotReads;val original=parent.state.detail;val selection=parent.state.selection;ready(m);m.submit(m.presentation);runCurrent();val old=m.presentation;parent.retryDetail(parent.control);runCurrent();p.pending[0].complete(AppointmentSlotRead(p.calls[0],emptyList()));runCurrent();m.open(old);m.retry(old);runCurrent();assertFalse(m.available);assertNull(m.presentation);assertNull(m.state.read);assertEquals(original,parent.state.detail);assertEquals(selection,parent.state.selection)
    }
    @Test fun foreignIntentAndInvalidRangeFromCustomPortAreRejected()=check {_,_,m,p,_->
        ready(m);m.submit(m.presentation);runCurrent();p.pending[0].complete(AppointmentSlotRead(p.calls[0].copy(day="2026-11-03"),emptyList()));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,m.state.problem);m.retry(m.presentation);runCurrent();p.pending[1].complete(AppointmentSlotRead(p.calls[1],listOf(AppointmentSlotCandidate("2026-11-02T04:00:00Z","2026-11-02T03:00:00Z"))));runCurrent();assertEquals(ReadProblem.INVALID_PAYLOAD,m.state.problem);assertNull(m.state.read)
    }
    @Test fun cancellationKeepsInputWithoutAutomaticRetry()=check {_,_,m,p,_->
        ready(m);m.submit(m.presentation);runCurrent();p.pending[0].completeExceptionally(CancellationException("Synthetic read cancellation"));runCurrent();assertEquals(ReadProblem.UNAVAILABLE,m.state.problem);assertEquals("2026-11-02",m.state.day);assertEquals(1,p.calls.size);assertNull(m.state.read)
    }
    @Test fun missingSlotPortStaysUnavailable()=check {_,links,_,_,_->
        val m=AppointmentSlotReadViewModel(null,null);try {m.bind(links.state.reference!!,links.state.request!!,9001);m.open(m.presentation);assertFalse(m.available);assertFalse(m.state.presented)}finally {m.clear();m.viewModelScope.cancel()}
    }
}
