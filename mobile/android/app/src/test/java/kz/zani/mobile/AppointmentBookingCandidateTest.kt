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
class AppointmentBookingCandidateTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun ref(id:Int,business:Int,kind:AppointmentReferenceKind)=AppointmentReferenceDetail.decode(JSONObject().put("id",id).put("business",business).put("name","Synthetic reference").put("is_active",false).toString(),kind)!!
    private fun reader()=ReadTransport {q->val id=q.path.trimEnd('/').substringAfterLast('/');val name=when {
        q.path.endsWith("/bootstrap/")->"bootstrap";q.path.endsWith("/appointments/")->"appointments-${q.query["business"]}"
        q.path.startsWith("/api/services/")->"service-reference-$id";q.path.startsWith("/api/resources/")->"resource-reference-$id"
        q.path.startsWith("/api/mobile/v1/clients/")->"client-${q.query["business"]}-$id";else->"appointment-${q.query["business"]}-$id"};ReadResponse(200,fixture(name))}
    private fun slots()=APIAppointmentSlotRepository(ReadTransport {q->val a=JSONObject(fixture("appointment-slot-read-fixtures")).getJSONArray("reads");val row=(0 until a.length()).map {a.getJSONObject(it)}.first {val x=it.getJSONObject("query");x.keys().asSequence().associateWith {k->x.getString(k)}==q.query};ReadResponse(200,row.getString("response_json"))})
    private fun check(block:suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,AppointmentSlotReadViewModel,APIReadRepository,APIAppointmentReferenceRepository)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val transport=reader();val repo=APIReadRepository(transport);val refs=APIAppointmentReferenceRepository(transport);val links=AppointmentRelationsViewModel(repo,refs,slots());val port=FixtureAppointmentBookingPort.fromJSON(fixture("appointment-booking"));val life=FixtureAppointmentTerminalPort.fromJSON(fixture("appointment-lifecycle"),fixture("appointment-terminal"));val parent=AgendaViewModel(repo,initialDay={"2026-10-28"},relations=links,lifecyclePort=life,bookingPort=port,bookingClients=repo,bookingReferences=refs)
        try {parent.start();runCurrent();parent.detail(501);runCurrent();block(parent,links,links.slotReads,repo,refs)}finally {links.clear();links.slotReads.viewModelScope.cancel();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private fun TestScope.select(links:AppointmentRelationsViewModel,index:Int=0,mode:AppointmentSlotResourceMode=AppointmentSlotResourceMode.LINKED) {
        if(links.state.selected!=null)links.back(links.presentation);links.openReference(AppointmentReferenceKind.SERVICE,links.presentation);runCurrent();val s=links.slotReads;s.open(s.presentation);s.setDayInput("2026-11-02",s.inputControl);s.choose(mode,s.presentation);s.submit(s.presentation);runCurrent();s.selectCandidate(index,s.presentation)
    }
    @Test fun sharedTypedCandidateScopeIndexPrecisionAndNoCreateAuthority() {
        val cases=JSONObject(fixture("appointment-booking-candidate-time")).getJSONArray("cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val sourceBusiness=row.getInt("source_business");val boot=JSONObject(fixture("bootstrap"));val businesses=boot.getJSONArray("businesses")
            for(j in 0 until businesses.length())if(businesses.getJSONObject(j).getInt("id")==sourceBusiness)businesses.getJSONObject(j).put("timezone",row.getString("source_timezone"))
            if(boot.getJSONObject("active_business").getInt("id")==sourceBusiness)boot.getJSONObject("active_business").put("timezone",row.getString("source_timezone"))
            val session=AgendaSession();session.install(JsonContracts.bootstrap(boot.toString()));val page=JsonContracts.appointments(fixture("appointments-$sourceBusiness"));val scope=session.begin(sourceBusiness,page.date);session.receive(page,scope)
            val source=AppointmentBookingSource(session.beginDetail(if(sourceBusiness==101)501 else 601),1,if(sourceBusiness==101)7001 else 7003,row.getInt("source_service"),if(row.isNull("source_resource"))null else row.getInt("source_resource"))
            val business=Business(row.getInt("context_business"),"Synthetic Business",row.getString("context_timezone"));val service=ref(row.getInt("context_service"),business.id,AppointmentReferenceKind.SERVICE);val resource=if(row.isNull("context_resource"))null else ref(row.getInt("context_resource"),business.id,AppointmentReferenceKind.RESOURCE)
            val selected=AppointmentSlotIntent.make(business,service,resource,row.getString("day"))?.let {intent->AppointmentSlotRead.decode(row.getString("response_json"),intent)?.let {read->AppointmentSlotReadContext.make(business,service,resource,read)?.review(row.getInt("index"))}}?.let {AppointmentBookingCandidateTime.make(source,it)}
            assertEquals(row.getString("name"),row.getBoolean("valid"),selected!=null)
            selected?.let {assertEquals(it.review.candidate!!.startAt,it.rawStart);assertTrue(it.validFor(source));assertFalse(it.validFor(source.copy(epoch=2)));assertNull(SyntheticAppointmentBookingGrant(sourceBusiness,source.read.id,5001,false).authorization(source))}
        }
    }
    @Test fun stableSlotTypingExplicitTimeOnlyTransferAndNoOriginalMutation()=check {parent,links,s,_,_->
        links.openReference(AppointmentReferenceKind.SERVICE,links.presentation);runCurrent();s.open(s.presentation);val input=s.inputControl!!;val old=s.presentation;s.setDayInput("2026-11-0",input);s.setDayInput("2026-11-02",input);s.choose(AppointmentSlotResourceMode.LINKED,old);assertEquals("2026-11-02",s.state.day);assertEquals(input,s.inputControl);assertNull(s.state.resourceMode)
        s.choose(AppointmentSlotResourceMode.UNSPECIFIED,s.presentation);s.submit(s.presentation);runCurrent();s.selectCandidate(0,s.presentation);val review=s.state.review!!;val bridge=parent.bookingCandidateControl(parent.control,links.presentation,s.presentation,review)!!;val booking=parent.booking!!;val before=parent.state
        val peer=parent.lifecycle!!;peer.prepare(AppointmentLifecycleAction.CONFIRM,peer.control);peer.back(peer.control);parent.useBookingCandidate(bridge);assertFalse(booking.presented);assertEquals("",booking.rawStart)
        val current=parent.bookingCandidateControl(parent.control,links.presentation,s.presentation,review)!!;parent.useBookingCandidate(current);assertTrue(booking.presented);assertEquals("2026-11-02T04:15:00Z",booking.rawStart);assertNull(booking.client);assertNull(booking.service);assertNull(booking.resource);assertFalse(booking.canReview);assertEquals(0,booking.retainedAttemptCount);assertNull(links.state.selected);assertNull(s.state.context);assertEquals(before,parent.state)
        s.setDayInput("stale",input);parent.useBookingCandidate(current);assertEquals("",s.state.day);assertEquals(current.time.rawStart,booking.rawStart)
        booking.load(AppointmentBookingReadKind.CLIENT,booking.control);booking.load(AppointmentBookingReadKind.SERVICE,booking.control);assertNull(booking.resource);assertFalse(booking.canReview);booking.chooseClear(booking.control);assertTrue(booking.canReview)
        parent.backBooking(parent.bookingEntryControl,booking.control);select(links,1,AppointmentSlotResourceMode.UNSPECIFIED);val kept=parent.bookingCandidateControl(parent.control,links.presentation,s.presentation,s.state.review!!)!!;parent.useBookingCandidate(kept);assertEquals(kept.time.rawStart,booking.rawStart);assertEquals(7001,booking.client!!.id);assertEquals(8001,booking.service!!.id);assertEquals(AppointmentRescheduleResource.Clear,booking.resource)
    }
    @Test fun staleBackMatchingReadRelatedParentBusinessAndUnknownCannotTransferAgain()=check {parent,links,s,_,_->
        fun control()=parent.bookingCandidateControl(parent.control,links.presentation,s.presentation,s.state.review!!)
        select(links);val oldBack=control()!!;s.backToCandidates(s.presentation);s.selectCandidate(0,s.presentation);parent.useBookingCandidate(oldBack);assertFalse(parent.booking!!.presented)
        val oldRead=control()!!;val context=s.state.context;s.refresh(s.presentation);runCurrent();s.selectCandidate(0,s.presentation);parent.useBookingCandidate(oldRead);assertEquals(context,s.state.context);assertFalse(parent.booking!!.presented)
        val oldRelated=control()!!;select(links);parent.useBookingCandidate(oldRelated);assertFalse(parent.booking!!.presented)
        val oldParent=control()!!;parent.retryDetail(parent.control);runCurrent();select(links);parent.useBookingCandidate(oldParent);assertFalse(parent.booking!!.presented)
        val oldBusiness=control()!!;parent.load(202,"2026-10-28");runCurrent();parent.load(101,"2026-10-28");runCurrent();parent.detail(501);runCurrent();select(links);parent.useBookingCandidate(oldBusiness);assertFalse(parent.booking!!.presented)
        val current=control()!!;assertEquals(9001,current.review.context.resource!!.id);parent.useBookingCandidate(current);val booking=parent.booking!!;assertNull(booking.resource);assertNull(booking.client);assertNull(booking.service)
        booking.load(AppointmentBookingReadKind.CLIENT,booking.control);booking.load(AppointmentBookingReadKind.SERVICE,booking.control);booking.chooseClear(booking.control);booking.prepareReview(booking.control);booking.submit(booking.control);assertEquals(AppointmentBookingPhase.UNKNOWN,booking.submission!!.phase);val attempt=booking.submission!!.attempt;val body=JSONObject(attempt.body);assertEquals(setOf("business","client","service","start_at","resource"),body.keys().asSequence().toSet());assertEquals(current.time.rawStart,body.getString("start_at"));assertTrue(body.isNull("resource"))
        parent.retryDetail(parent.control);runCurrent();select(links);assertTrue(booking.blocked);assertNull(control());parent.useBookingCandidate(current);assertEquals(1,booking.retainedAttemptCount);parent.load(202,"2026-10-28");runCurrent();parent.load(101,"2026-10-28");runCurrent();parent.detail(501);runCurrent();assertTrue(booking.blocked);assertFalse(booking.canOpen);assertEquals(1,booking.retainedAttemptCount)
    }
}
