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
class AppointmentSlotReviewTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun ref(kind:AppointmentReferenceKind,id:Int)=AppointmentReferenceDetail.decode(fixture("${if(kind==AppointmentReferenceKind.SERVICE)"service" else "resource"}-reference-$id"),kind)!!
    private fun business(o:JSONObject)=Business(o.getInt("id"),o.getString("name"),o.getString("timezone"))
    private class Slots:AppointmentSlotRepository {
        val calls=mutableListOf<AppointmentSlotIntent>();val pending=mutableListOf<CompletableDeferred<AppointmentSlotRead>>()
        override suspend fun slots(intent:AppointmentSlotIntent):AppointmentSlotRead {calls+=intent;return CompletableDeferred<AppointmentSlotRead>().also {pending+=it}.await()}
    }
    private fun answer(intent:AppointmentSlotIntent)=AppointmentSlotRead.decode("[{\"start_at\":\"2026-11-02T04:15:00Z\",\"end_at\":\"2026-11-02T05:00:00Z\"},{\"start_at\":\"2026-11-02T06:30:00Z\",\"end_at\":\"2026-11-02T07:10:00Z\"}]",intent)!!
    private fun check(block:suspend TestScope.(AgendaViewModel,AppointmentRelationsViewModel,AppointmentSlotReadViewModel,Slots)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val slots=Slots()
        val repository=APIReadRepository(ReadTransport {q->val name=when {q.path.endsWith("/bootstrap/")->"bootstrap";q.path.endsWith("/appointments/")->"appointments-${q.query["business"]}";else->"appointment-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}"};ReadResponse(200,fixture(name))})
        val refs=APIAppointmentReferenceRepository(ReadTransport {q->ReadResponse(200,fixture("${if(q.path.contains("/services/"))"service" else "resource"}-reference-${q.path.trimEnd('/').substringAfterLast('/')}"))});val links=AppointmentRelationsViewModel(repository,refs,slots);val parent=AgendaViewModel(repository,initialDay={"2026-10-28"},relations=links)
        try {parent.start();runCurrent();parent.openDetail(501,parent.control);runCurrent();links.openReference(AppointmentReferenceKind.SERVICE,links.presentation);runCurrent();val model=links.slotReads;model.open(model.presentation);model.setDay("2026-11-02",model.presentation);model.choose(AppointmentSlotResourceMode.LINKED,model.presentation);block(parent,links,model,slots)}
        finally {links.clear();links.slotReads.viewModelScope.cancel();links.profile.viewModelScope.cancel();links.viewModelScope.cancel();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sharedScopedContextAndReturnedIndexMembershipCases() {
        val rows=JSONObject(fixture("appointment-slot-review-cases")).getJSONArray("cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val source=ref(AppointmentReferenceKind.SERVICE,8001);val selected=if(row.getBoolean("request_resource"))ref(AppointmentReferenceKind.RESOURCE,9001) else null;val intent=AppointmentSlotIntent.make(Business(101,"Synthetic Business A",row.getString("intent_timezone")),source,selected,"2026-11-02")!!;val read=AppointmentSlotRead.decode(row.getString("response_json"),intent);val service=AppointmentReferenceDetail.decode(row.getString("context_service_json"),AppointmentReferenceKind.SERVICE);val resource=AppointmentReferenceDetail.decode(row.getString("context_resource_json"),AppointmentReferenceKind.RESOURCE);val context=if(service!=null && read!=null)AppointmentSlotReadContext.make(business(row.getJSONObject("context_business")),service,resource,read) else null
            assertEquals(row.getString("name"),row.getBoolean("context_valid"),context!=null);val review=context?.review(row.getInt("index"));assertEquals(row.getString("name"),row.getBoolean("review_valid"),review!=null)
            if(context!=null){assertEquals(row.getJSONObject("context_service").getString("name"),context.service.name);if(context.resource!=null)assertEquals(row.getJSONObject("context_resource").getString("name"),context.resource.name);assertEquals(intent,context.read.intent);assertEquals(intent.resource,context.resource?.id)}
            if(review!=null){assertTrue(review.validFor(context!!));assertEquals(row.getInt("index"),review.index);assertEquals(context.read.candidates[review.index],review.candidate)}
        }
    }
    @Test fun noCandidateCanBeChosenBeforeACompletedCurrentRead()=check {_,_,m,p->
        m.selectCandidate(0,m.presentation);assertNull(m.state.review);m.submit(m.presentation);runCurrent();m.selectCandidate(0,m.presentation);assertNull(m.state.review);assertNull(m.state.context);p.pending[0].complete(answer(p.calls[0]));runCurrent()
    }
    @Test fun onlyOwnReturnedCandidateIndexCanCreateReadReview()=check {_,l,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();val current=m.presentation;m.selectCandidate(-1,current);m.selectCandidate(2,current);m.selectCandidate(Int.MAX_VALUE,current);assertNull(m.state.review);assertEquals(current,m.presentation);m.selectCandidate(1,current);val review=m.state.review!!;assertEquals(1,review.index);assertEquals(answer(p.calls[0]).candidates[1],review.candidate);assertEquals(l.state.reference,review.context.service);assertEquals(9001,review.context.resource!!.id);assertEquals(101,review.context.business.id)
    }
    @Test fun listCallbacksCannotReplaceAReviewAfterSelection()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();val old=m.presentation;m.selectCandidate(1,old);val control=m.presentation;val review=m.state.review;m.selectCandidate(0,old);m.backToCandidates(old);m.edit(old);m.refresh(old);runCurrent();assertEquals(control,m.presentation);assertEquals(review,m.state.review);assertEquals(1,p.calls.size)
    }
    @Test fun reviewBackKeepsExactReadWithoutStartingAnotherGet()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();val context=m.state.context;m.selectCandidate(1,m.presentation);val old=m.presentation;m.backToCandidates(old);val current=m.presentation;m.selectCandidate(0,old);assertNull(m.state.review);assertEquals(context,m.state.context);assertEquals(1,p.calls.size);m.selectCandidate(0,current);assertEquals(0,m.state.review!!.index)
    }
    @Test fun manualRereadImmediatelyInvalidatesReviewButKeepsExplicitIntent()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(1,m.presentation);val old=m.presentation;m.refresh(old);runCurrent();assertNull(m.state.review);assertNull(m.state.context);assertNull(m.state.read);assertTrue(m.state.loading);assertEquals("2026-11-02",m.state.day);assertEquals(AppointmentSlotResourceMode.LINKED,m.state.resourceMode);m.refresh(old);m.selectCandidate(0,old);runCurrent();assertEquals(2,p.calls.size);assertEquals(p.calls[0],p.calls[1]);p.pending[1].complete(answer(p.calls[1]));runCurrent()
    }
    @Test fun matchingRereadDoesNotRestoreChoiceOrAcceptOldListTicket()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();val value=answer(p.calls[0]);p.pending[0].complete(value);runCurrent();val list=m.presentation;m.selectCandidate(1,list);val old=m.presentation;val oldContext=m.state.context;m.refresh(old);runCurrent();p.pending[1].complete(value);runCurrent();val current=m.presentation;m.selectCandidate(0,list);m.selectCandidate(1,old);assertNull(m.state.review);assertEquals(oldContext,m.state.context);assertEquals(current,m.presentation);m.selectCandidate(0,current);assertEquals(0,m.state.review!!.index)
    }
    @Test fun errorAndEmptyRereadCannotPresentPreviousSelectedRange()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(1,m.presentation);m.refresh(m.presentation);runCurrent();p.pending[1].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(m.state.review);assertNull(m.state.context);assertEquals(ReadProblem.DENIED,m.state.problem);m.retry(m.presentation);runCurrent();p.pending[2].complete(AppointmentSlotRead(p.calls[2],emptyList()));runCurrent();m.selectCandidate(0,m.presentation);assertNull(m.state.review);assertTrue(m.state.context!!.read.candidates.isEmpty())
    }
    @Test fun editClearsReadEvidenceAndRetainsRawDateResourceChoice()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(0,m.presentation);val old=m.presentation;m.edit(old);assertTrue(m.editing);assertNull(m.state.review);assertNull(m.state.context);assertNull(m.state.read);assertEquals("2026-11-02",m.state.day);assertEquals(AppointmentSlotResourceMode.LINKED,m.state.resourceMode);m.selectCandidate(1,old);assertNull(m.state.review)
    }
    @Test fun parentRefreshAndLateOldResponseCannotReviveReadContext()=check {parent,_,m,p->
        m.submit(m.presentation);runCurrent();val old=m.presentation;parent.retryDetail(parent.control);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(0,old);m.backToCandidates(old);assertNull(m.presentation);assertNull(m.state.context);assertNull(m.state.review);assertFalse(m.available)
    }
    @Test fun readReviewDoesNotMutateAppointmentListDayOrScope()=check {parent,_,m,p->
        val before=parent.state;m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(1,m.presentation);m.backToCandidates(m.presentation);m.selectCandidate(0,m.presentation);assertEquals(before,parent.state);assertEquals(1,p.calls.size)
    }
    @Test fun closeReopenInvalidatesOldReviewAndReturnsToEmptyForm()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(0,m.presentation);val old=m.presentation;m.close(old);m.open(m.presentation);m.selectCandidate(1,old);m.backToCandidates(old);assertTrue(m.editing);assertEquals("",m.state.day);assertNull(m.state.resourceMode);assertNull(m.state.context);assertNull(m.state.review)
    }
    @Test fun mutablePortCandidateListCannotChangeRetainedReadReview()=check {_,_,m,p->
        m.submit(m.presentation);runCurrent();val rows=answer(p.calls[0]).candidates.toMutableList();p.pending[0].complete(AppointmentSlotRead(p.calls[0],rows));runCurrent();m.selectCandidate(1,m.presentation);val review=m.state.review;rows.clear();assertEquals(review,m.state.review);assertEquals(2,m.state.context!!.read.candidates.size);assertNotNull(m.state.review!!.candidate)
    }
    @Test fun businessSwitchInvalidatesOldReadReviewCallbacks()=check {parent,_,m,p->
        m.submit(m.presentation);runCurrent();p.pending[0].complete(answer(p.calls[0]));runCurrent();m.selectCandidate(0,m.presentation);val old=m.presentation;parent.load(202,"2026-10-28");runCurrent();m.selectCandidate(1,old);m.backToCandidates(old);m.refresh(old);runCurrent();assertNull(m.presentation);assertNull(m.state.review);assertNull(m.state.context);assertEquals(1,p.calls.size)
    }
}
