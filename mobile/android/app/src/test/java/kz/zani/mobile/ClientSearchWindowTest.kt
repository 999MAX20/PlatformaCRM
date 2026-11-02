package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ClientSearchWindowTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(q:String)=JsonContracts.clients(FixtureClientSearch.list(fixture("client-search-catalogue-101"),101,q).body)
    private fun profile(id:Int=1754)=JsonContracts.clientProfile(FixtureClientSearch.profile(fixture("client-search-catalogue-101"),101,id).body)
    private class Controlled:ClientSearchRepository {
        val requests=mutableListOf<ReadRequest>();val searches=mutableListOf<CompletableDeferred<ClientList>>();val profiles=mutableListOf<CompletableDeferred<ClientProfile>>()
        override suspend fun searchClients(business:Int,search:String):ClientList {requests+=ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "$business","limit" to "50","search" to search));return CompletableDeferred<ClientList>().also {searches+=it}.await()}
        override suspend fun clientProfile(business:Int,id:Int):ClientProfile {requests+=ReadRequest("/api/mobile/v1/clients/$id/",mapOf("business" to "$business"));return CompletableDeferred<ClientProfile>().also {profiles+=it}.await()}
    }
    private fun check(block:suspend TestScope.(ClientSearchModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val r=Controlled();val m=ClientSearchModel(r,backgroundScope);val ctx=ClientSearchContext(101,1);m.bind(ctx);m.open(ctx)
        try {block(m,r)} finally {m.bind(null);m.profile.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun continuousRawInputSupersedesPendingSearchWithoutExtraSubmitOrLateWindowChange()=check {m,r->
        val input=m.inputControl!!;val raw="\u001C catalogue \n";assertTrue(r.requests.isEmpty());m.update(raw,input=input);val old=m.control!!;m.submit(expected=old);runCurrent();m.submit(expected=m.control);m.clear(expected=old);runCurrent();assertEquals(1,r.searches.size);assertEquals(raw,m.state.query);assertEquals("catalogue",r.requests[0].query["search"])
        m.update("catalogue 05",input=input);m.submit(expected=m.control);runCurrent();r.searches[1].complete(page("catalogue 05"));runCurrent();val fresh=m.control!!;r.searches[0].complete(page("catalogue"));runCurrent();assertEquals(fresh,m.control);assertEquals(input,m.inputControl);assertEquals("catalogue 05",m.state.submitted);assertTrue(m.state.items.any {it.id==1754})
    }
    @Test fun oldWindowCannotOpenSameIdOrClearOrResubmitAfterAnotherQuery()=check {m,r->
        m.update("catalogue 05",input=m.inputControl);m.submit(expected=m.control);runCurrent();r.searches[0].complete(page("catalogue 05"));runCurrent();val old=m.control!!
        m.update("catalogue",input=m.inputControl);m.submit(expected=m.control);runCurrent();r.searches[1].complete(page("catalogue"));runCurrent();m.openClient(1754,expected=old);m.clear(expected=old);m.submit(expected=old);runCurrent();assertEquals(2,r.searches.size);assertTrue(r.profiles.isEmpty());assertTrue(m.state.items.any {it.id==1754});assertEquals("catalogue",m.state.query);assertNull(m.state.profileSelection)
    }
    @Test fun profileRetryUsesIndependentReadAndOldBackCannotCloseNewPendingOrCompletedRead()=check {m,r->
        m.update("catalogue",input=m.inputControl);m.submit(expected=m.control);runCurrent();r.searches[0].complete(page("catalogue"));runCurrent();val input=m.inputControl!!;m.openClient(1754,expected=m.control);runCurrent();val pending=m.control!!;m.retryProfile(expected=pending);m.update("old",input=input);runCurrent();assertEquals(1,r.profiles.size);assertEquals("catalogue",m.state.query)
        r.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();val denied=m.control!!;m.retryProfile(expected=denied);runCurrent();m.backProfile(expected=denied);m.retryProfile(expected=denied);runCurrent();assertEquals(2,r.profiles.size);assertTrue(m.profile.state.loading);assertEquals(1754,m.state.selectedID)
        r.profiles[1].complete(profile());runCurrent();val result=m.control!!;m.back(control=result,workReturn=m.profile.workReturnControl);m.close(expected=result);m.update("old",input=input);runCurrent();assertNotNull(m.state.selection);assertNull(m.state.profileSelection);assertEquals("catalogue",m.state.query);assertEquals(50,m.state.items.size);assertTrue(m.state.partial)
    }
    @Test fun explicitClearBlankAndNotesMatchKeepSourceWindowAndDoNotRefilterVisibleFields()=check {m,r->
        val input=m.inputControl!!;m.update("Before clear",input=input);m.clear(expected=m.control);m.update("old",input=input);runCurrent();assertTrue(r.requests.isEmpty());assertEquals("",m.state.query);assertFalse(m.state.showsEmpty)
        m.submit(expected=m.control);runCurrent();r.searches[0].complete(page(""));runCurrent();assertEquals(50,m.state.items.size);assertEquals(56,m.state.total);assertTrue(m.state.partial)
        m.update("fixture-note-tag",input=m.inputControl);m.submit(expected=m.control);runCurrent();r.searches[1].complete(page("fixture-note-tag"));runCurrent();assertEquals(listOf(1702),m.state.items.map {it.id});assertEquals(1,m.state.total)
    }
    @Test fun newEpochAndCancellationRevokeOldActionsWhileRetainingManualTextForReadRetry()=check {m,r->
        m.update("Recoverable",input=m.inputControl);m.submit(expected=m.control);runCurrent();val pending=m.control!!;r.searches[0].cancel();runCurrent();assertEquals("Recoverable",m.state.query);assertFalse(m.state.loading);assertFalse(m.state.showsEmpty);m.submit(expected=pending);runCurrent();assertEquals(1,r.searches.size)
        val old=m.control!!;val input=m.inputControl!!;val next=ClientSearchContext(101,2);m.bind(next);m.open(next);m.update("old",input=input);m.submit(expected=old);m.clear(expected=old);m.close(expected=old);m.openClient(1754,expected=old);runCurrent();assertEquals(next,m.state.selection!!.context);assertEquals("",m.state.query);assertEquals(1,r.requests.size);assertTrue(r.profiles.isEmpty())
    }
    @Test fun sharedRawUnicodeQueriesKeepExactInputAndInvalidateOnlyChangedPendingWindows()=runTest {
        val rows=org.json.JSONObject(fixture("client-search-raw-unicode-cases")).getJSONArray("cases")
        for(i in 0 until rows.length()) {
            val row=rows.getJSONObject(i);val before=row.getString("before");val after=row.getString("after");val changed=row.getBoolean("changed");val context=ClientSearchContext(101,1);val session=ClientSearchSession();session.bind(context);session.open(context);val owner=session.state.selection!!
            session.update(before,owner);val pending=session.begin(owner)!!;session.update(after,owner);assertEquals(after,session.state.query);assertEquals(!changed,session.accept(page(""),pending));val current=session.begin(owner)!!;assertEquals(row.getString("after_submitted"),current.query);assertTrue(session.accept(page(""),current))
            val repo=Controlled();val model=ClientSearchModel(repo,this);model.bind(context);model.open(context);val input=model.inputControl!!;model.update(before,input);model.submit(model.control);runCurrent();val prior=model.control;model.update(after,input);assertEquals(after,model.state.query);assertEquals(input,model.inputControl);assertEquals(changed,prior!=model.control);repo.searches.single().complete(page(""));runCurrent();assertEquals(!changed,model.state.loaded)
            if(changed){model.openClient(1754,prior);runCurrent();assertTrue(repo.profiles.isEmpty());model.submit(model.control);runCurrent();repo.searches.last().complete(page(""));runCurrent()};assertEquals(row.getString("after_submitted"),repo.requests.last().query["search"]);model.bind(null)
        }
    }
}
