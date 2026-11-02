package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.LoadedSearchViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LoadedSearchControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun feed(epoch:Int=1,generation:Int=1,business:Int=101)=LoadedSearchFeed.create(business,epoch,listOf(
        LoadedSearchSource(LoadedSearchKind.TASKS,LoadedSearchToken(LoadedSearchKind.TASKS,business,epoch,generation),LoadedSearchCoverage.LOADED,JsonContracts.tasks(fixture("tasks-$business")).items.map {LoadedSearchRow(it.id,it.title)}),
        LoadedSearchSource(LoadedSearchKind.CLIENTS,LoadedSearchToken(LoadedSearchKind.CLIENTS,business,epoch,generation),LoadedSearchCoverage.LOADED,JsonContracts.clients(fixture("clients-$business")).items.map {LoadedSearchRow(it.id,it.title)})
    ))
    private class Controlled:ReadTransport {
        val requests=mutableListOf<ReadRequest>();val pending=mutableListOf<CompletableDeferred<ReadResponse>>()
        override suspend fun get(request:ReadRequest):ReadResponse {requests+=request;return CompletableDeferred<ReadResponse>().also {pending+=it}.await()}
    }
    private fun check(block:suspend TestScope.(LoadedSearchViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=LoadedSearchViewModel(APIReadRepository(r))
        try {block(m,r)} finally {m.profile.viewModelScope.cancel();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sourceEntryIsLocalAndOldOrQueryHiddenHitCannotOpen()=check {m,r->
        assertNull(m.control);assertFalse(m.matches(null));assertNull(m.sourceTab(LoadedSearchKind.TASKS,null));m.reconcile(feed());val input=m.inputControl!!;m.searchInput("Alpha",input);val list=m.control!!;val hit=m.state.matches.first {it.identity.kind==LoadedSearchKind.TASKS}
        assertEquals(3,m.sourceTab(LoadedSearchKind.INBOX,list));assertTrue(r.requests.isEmpty());m.searchInput("Beta",input);m.open(hit,list);runCurrent();assertTrue(r.requests.isEmpty());assertNull(m.state.selected)
        m.reconcile(feed(generation=2));m.search("old",list);m.open(hit,list);assertNull(m.sourceTab(LoadedSearchKind.TASKS,list));runCurrent();assertEquals("Beta",m.state.query);assertTrue(r.requests.isEmpty())
    }
    @Test fun pendingAndDeniedRetryUseCapturedVisitWithoutUnsuppressingOldCandidate()=check {m,r->
        m.reconcile(feed());m.searchInput("Alpha",m.inputControl);val list=m.control!!;val hit=m.state.matches.first {it.identity.kind==LoadedSearchKind.TASKS};m.open(hit,list);runCurrent();val card=m.control!!
        m.open(hit,list);m.retry(card);m.back(list);m.search("old",list);runCurrent();assertEquals(1,r.requests.size);assertEquals("Alpha",m.state.query);assertNull(m.sourceTab(LoadedSearchKind.TASKS,card))
        r.pending[0].complete(ReadResponse(403,""));runCurrent();assertEquals(ReadProblem.DENIED,m.state.problem);assertFalse(m.state.matches.contains(hit));m.retry(card);runCurrent();val newer=m.control!!;m.back(card);m.retry(card);runCurrent();assertEquals(2,r.requests.size);assertEquals(newer,m.control)
        r.pending[1].complete(ReadResponse(200,fixture("task-101-1101")));runCurrent();m.back(newer);assertNull(m.state.selected);assertEquals("Alpha",m.state.query);assertFalse(m.state.matches.contains(hit));assertEquals(4,m.sourceTab(LoadedSearchKind.TASKS,m.control))
    }
    @Test fun oldSameHitBackRetryAndLateReadCannotCloseOrRestoreNewVisit()=check {m,r->
        m.reconcile(feed());m.search("Alpha",m.control);val hit=m.state.matches.first {it.identity.kind==LoadedSearchKind.TASKS};m.open(hit,m.control);runCurrent();val old=m.control!!;m.back(old);val list=m.control!!;m.open(hit,list);runCurrent();val newer=m.control!!;m.back(old);m.retry(old);runCurrent();assertEquals(2,r.requests.size);assertEquals(newer,m.control)
        val json=JSONObject(fixture("task-101-1101"));json.getJSONObject("task").put("title",JSONObject.NULL);r.pending[1].complete(ReadResponse(200,json.toString()));runCurrent();r.pending[0].complete(ReadResponse(200,fixture("task-101-1101")));runCurrent();assertNull(m.state.detail!!.title);assertNull(m.state.problem);assertFalse(m.state.matches.contains(hit))
    }
    @Test fun independentlyReadAppointmentRejectsInvalidRangeWithoutListFallback()=check {m,r->
        val detail=JsonContracts.detail(fixture("appointment-101-501"))
        val source=LoadedSearchSource(LoadedSearchKind.APPOINTMENTS,LoadedSearchToken(LoadedSearchKind.APPOINTMENTS,101,1,1),LoadedSearchCoverage.LOADED,listOf(LoadedSearchRow(501,detail.appointment.title)))
        m.reconcile(LoadedSearchFeed.create(101,1,listOf(source)));m.search("Synthetic",m.control);val hit=m.state.matches.single();m.open(hit,m.control);runCurrent()
        val json=JSONObject(fixture("appointment-101-501"));val row=json.getJSONObject("appointment");row.put("end_at",row.get("start_at"));r.pending[0].complete(ReadResponse(200,json.toString()));runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD,m.state.problem);assertNull(m.state.detail);assertFalse(m.state.matches.contains(hit));assertEquals(1,r.requests.size)
    }
    @Test fun newOwnerAndFeedRevokeOldClientRetryEntryAndLatePrivateProfile()=check {m,r->
        m.reconcile(feed());m.searchInput("Alpha",m.inputControl);val list=m.control!!;val hit=m.state.matches.first {it.identity.kind==LoadedSearchKind.CLIENTS};m.open(hit,list);runCurrent();val old=m.control!!;m.reconcile(feed(epoch=2,generation=2));r.pending[0].complete(ReadResponse(200,fixture("client-101-701")));runCurrent()
        assertNull(m.profile.state.detail);assertNull(m.state.selected);assertEquals("",m.state.query);m.search("old",list);m.retry(old);m.back(old);assertNull(m.sourceTab(LoadedSearchKind.CLIENTS,list));runCurrent();assertEquals(1,r.requests.size)
        m.reconcile(feed(epoch=3,generation=3,business=202));m.open(hit,list);m.search("old",old);runCurrent();assertEquals(202,m.state.feed.business);assertEquals("",m.state.query);assertTrue(m.state.suppressed.isEmpty());assertEquals(1,r.requests.size)
    }
    @Test fun sharedExactHeadersAcrossFourDetailsSuppressOldTitlesKeepQueryAndRejectLateOwnerReads()=check {m,r->
        val cases=JSONObject(fixture("loaded-search-exact-header-cases")).getJSONArray("cases")
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val before=row.getString("before_title");val after=if(row.isNull("after_title"))null else row.getString("after_title");val changed=row.getBoolean("changed");val epoch=2100+i
            for(kind in LoadedSearchKind.entries) {
                val id=when(kind){LoadedSearchKind.APPOINTMENTS->501;LoadedSearchKind.CLIENTS->701;LoadedSearchKind.INBOX->901;LoadedSearchKind.TASKS->1101};val file=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment-101-501";LoadedSearchKind.CLIENTS->"client-101-701";LoadedSearchKind.INBOX->"inbox-101-901";LoadedSearchKind.TASKS->"task-101-1101"};val field=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment";LoadedSearchKind.CLIENTS->"client";LoadedSearchKind.INBOX->"conversation";LoadedSearchKind.TASKS->"task"};val coverage=if(i%2==0)LoadedSearchCoverage.LOADED else LoadedSearchCoverage.PARTIAL
                fun rawFeed(title:String?,generation:Int,ownerEpoch:Int=epoch)=LoadedSearchFeed.create(101,ownerEpoch,listOf(LoadedSearchSource(kind,LoadedSearchToken(kind,101,ownerEpoch,generation),coverage,listOf(LoadedSearchRow(id,title)))))
                fun response(title:String?):ReadResponse {val obj=JSONObject(fixture(file));obj.getJSONObject(field).put("title",title ?: JSONObject.NULL);return ReadResponse(200,obj.toString())}
                m.back();m.reconcile(rawFeed(before,1));m.searchInput(" SHARED ",m.inputControl);val list=m.control!!;val oldHit=m.state.matches.single();val initial=r.requests.size;m.reconcile(rawFeed(after,1));assertEquals(changed,list!=m.control)
                if(changed){m.open(oldHit,list);m.search("old",list);runCurrent()};assertEquals(initial,r.requests.size);assertNull(m.state.selected);assertEquals(" SHARED ",m.state.query);assertEquals(after,m.state.feed.source(kind)!!.rows.single().title);assertEquals(coverage,m.state.coverage(m.state.feed.source(kind)!!))
                m.reconcile(rawFeed(before,2));val hit=m.state.matches.single();m.open(hit,m.control);runCurrent();val card=m.control!!;r.pending.last().complete(response(after));runCurrent();val actual=if(kind==LoadedSearchKind.CLIENTS)m.profile.state.detail?.client?.title else m.state.detail?.title
                assertNull(m.state.problem);assertFalse(m.state.loading);assertEquals(after,actual);assertEquals(changed,hit.identity in m.state.suppressed);assertEquals(!changed,hit in m.state.matches);assertEquals(if(changed)LoadedSearchCoverage.PARTIAL else coverage,m.state.coverage(m.state.feed.source(kind)!!))
                if(changed){m.retry(card);runCurrent();r.pending.last().complete(response(before));runCurrent();assertEquals(hit.token,m.state.suppressed[hit.identity]);assertTrue(m.state.matches.isEmpty())}
                m.back(m.control);assertEquals(" SHARED ",m.state.query);assertNull(m.state.selected);assertNull(m.state.detail);assertNull(m.profile.state.detail);m.reconcile(rawFeed(before,3));assertEquals(1,m.state.matches.size);assertTrue(m.state.suppressed.isEmpty())
                val fresh=m.state.matches.single();m.open(fresh,m.control);runCurrent();val pending=r.pending.last();m.reconcile(rawFeed(after,3));if(changed){assertNull(m.state.selected);assertFalse(m.state.loading)};pending.complete(response(before));runCurrent();if(changed){assertNull(m.state.selected);assertNull(m.state.detail);assertNull(m.profile.state.detail)}else assertEquals(fresh,m.state.selected)
                val stale=m.control;m.reconcile(rawFeed(before,4,epoch+100));m.search("old epoch",stale);m.retry(stale);runCurrent();assertTrue(m.state.query.isEmpty());assertNull(m.state.selected);assertEquals(epoch+100,m.state.feed.epoch)
                val route="/api/mobile/v1/${if(kind==LoadedSearchKind.INBOX)"inbox" else kind.key}/$id/";assertTrue(r.requests.drop(initial).all {it.path==route && it.query==(if(kind==LoadedSearchKind.INBOX)mapOf("business" to "101","limit" to "30")else mapOf("business" to "101"))})
            }
        }
    }
    @Test fun feedABARevokesOldInputRowAndSourceTabWhileUnrelatedSourceKeepsPendingReadTicket()=check {m,r->
        fun rawFeed(title:String,extra:Boolean=false):LoadedSearchFeed {val sources=mutableListOf(LoadedSearchSource(LoadedSearchKind.TASKS,LoadedSearchToken(LoadedSearchKind.TASKS,101,2400,1),LoadedSearchCoverage.LOADED,listOf(LoadedSearchRow(1101,title))));if(extra)sources+=LoadedSearchSource(LoadedSearchKind.CLIENTS,LoadedSearchToken(LoadedSearchKind.CLIENTS,101,2400,1),LoadedSearchCoverage.PARTIAL,listOf(LoadedSearchRow(701,"Shared extra")));return LoadedSearchFeed.create(101,2400,sources)}
        val original="Shared e\u0301";m.reconcile(rawFeed(original));m.searchInput("Shared",m.inputControl);val old=m.control!!;val hit=m.state.matches.single();m.reconcile(rawFeed(original));assertEquals(old,m.control);m.reconcile(rawFeed("Shared é"));m.reconcile(rawFeed(original));val current=m.control!!;m.search("stale",old);m.open(hit,old);runCurrent();assertNotEquals(old,current);assertTrue(r.requests.isEmpty());assertEquals("Shared",m.state.query);assertNull(m.sourceTab(LoadedSearchKind.TASKS,old))
        m.open(hit,current);runCurrent();val card=m.control!!;m.reconcile(rawFeed(original,true));val replacement=m.control!!;m.back(card);m.retry(card);runCurrent();assertNotEquals(card,replacement);assertEquals(hit,m.state.selected);assertTrue(m.state.loading);assertEquals(1,r.requests.size)
        val objectRead=JSONObject(fixture("task-101-1101"));objectRead.getJSONObject("task").put("title",original);r.pending[0].complete(ReadResponse(200,objectRead.toString()));runCurrent();assertFalse(m.state.loading);assertNull(m.state.problem);assertEquals(original,m.state.detail!!.title);assertEquals(hit,m.state.selected)
        m.back(m.control);m.search("Shared e",m.control);assertNull(m.state.selected);assertNull(m.state.detail);assertEquals(LoadedSearchCoverage.PARTIAL,m.state.feed.source(LoadedSearchKind.CLIENTS)!!.coverage)
    }
    @Test fun sharedRawQueriesRetainContinuousInputRevokeSameRowActionsAndKeepIndependentFourKindReads()=check {m,r->
        val cases=JSONObject(fixture("loaded-search-query-window-cases")).getJSONArray("cases")
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val before=row.getString("before");val after=row.getString("after");val title=row.getString("title");val changed=row.getBoolean("changed");val epoch=2700+i
            for(kind in LoadedSearchKind.entries) {
                val id=when(kind){LoadedSearchKind.APPOINTMENTS->501;LoadedSearchKind.CLIENTS->701;LoadedSearchKind.INBOX->901;LoadedSearchKind.TASKS->1101};val file=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment-101-501";LoadedSearchKind.CLIENTS->"client-101-701";LoadedSearchKind.INBOX->"inbox-101-901";LoadedSearchKind.TASKS->"task-101-1101"};val field=when(kind){LoadedSearchKind.APPOINTMENTS->"appointment";LoadedSearchKind.CLIENTS->"client";LoadedSearchKind.INBOX->"conversation";LoadedSearchKind.TASKS->"task"};val coverage=if(i%2==0)LoadedSearchCoverage.LOADED else LoadedSearchCoverage.PARTIAL
                fun rawFeed(ownerEpoch:Int)=LoadedSearchFeed.create(101,ownerEpoch,listOf(LoadedSearchSource(kind,LoadedSearchToken(kind,101,ownerEpoch,1),coverage,listOf(LoadedSearchRow(id,title)))))
                m.back();val provided=rawFeed(epoch);m.reconcile(provided);val input=m.inputControl!!;m.searchInput(before,input);val old=m.control!!;val hit=m.state.matches.single();m.searchInput(after,input);val current=m.control!!;val start=r.requests.size
                assertEquals(after,m.state.query);assertEquals(input,m.inputControl);assertEquals(changed,old!=current);assertEquals(listOf(hit),m.state.matches)
                if(changed){m.open(hit,old);m.search("old action-input",old);assertNull(m.sourceTab(kind,old));runCurrent()};assertEquals(start,r.requests.size);assertNull(m.state.selected);assertEquals(after,m.state.query);assertEquals(provided,m.state.feed);assertEquals(coverage,m.state.coverage(m.state.feed.source(kind)!!));assertTrue(m.state.suppressed.isEmpty())
                m.searchInput(after,input);assertEquals(current,m.control);assertEquals(input,m.inputControl);m.searchInput(before,input);m.searchInput(after,input)
                if(changed){m.open(hit,current);runCurrent();assertNotEquals(current,m.control);assertNull(m.sourceTab(kind,current))};val ready=m.control!!;assertEquals(kind.tab,m.sourceTab(kind,ready))
                m.open(hit,ready);runCurrent();val card=m.control!!;m.searchInput("hidden",input);m.open(hit,ready);m.retry(card);runCurrent();assertNull(m.inputControl);assertTrue(m.state.loading);assertEquals(after,m.state.query);assertEquals(start+1,r.requests.size)
                val obj=JSONObject(fixture(file));obj.getJSONObject(field).put("title",title);r.pending.last().complete(ReadResponse(200,obj.toString()));runCurrent();val actual=if(kind==LoadedSearchKind.CLIENTS)m.profile.state.detail?.client?.title else m.state.detail?.title
                assertFalse(m.state.loading);assertNull(m.state.problem);assertEquals(title,actual);assertTrue(m.state.suppressed.isEmpty());m.back(m.control);val returned=m.inputControl!!;m.searchInput("old Back",input);m.open(hit,ready);runCurrent();assertNotEquals(input,returned);assertEquals(after,m.state.query);assertNull(m.state.selected);assertEquals(start+1,r.requests.size)
                m.searchInput("__not_in_loaded_title__",returned);assertTrue(m.state.matches.isEmpty());assertTrue(m.state.showsNoMatches);assertEquals(provided,m.state.feed);assertEquals(coverage,m.state.coverage(m.state.feed.source(kind)!!))
                val prior=m.inputControl!!;val action=m.control!!;m.reconcile(rawFeed(epoch+100));m.searchInput("old epoch",prior);m.open(hit,action);runCurrent();assertTrue(m.state.query.isEmpty());assertNull(m.state.selected);assertEquals(epoch+100,m.state.feed.epoch);assertEquals(start+1,r.requests.size)
                val expected=if(kind==LoadedSearchKind.INBOX)mapOf("business" to "101","limit" to "30")else mapOf("business" to "101");val route="/api/mobile/v1/${if(kind==LoadedSearchKind.INBOX)"inbox" else kind.key}/$id/";assertEquals(route,r.requests.last().path);assertEquals(expected,r.requests.last().query)
            }
        }
    }
}
