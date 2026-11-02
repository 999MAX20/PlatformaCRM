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
class ClientServerSearchTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(business: Int,query: String)=JsonContracts.clients(FixtureClientSearch.list(fixture("client-search-catalogue-$business"),business,query).body)
    private val a=ClientSearchContext(101,20)
    private inner class Repository : ClientRepository,ClientSearchRepository {
        val requests=mutableListOf<ReadRequest>();var holdSearch=false;var holdProfile=false
        val searches=mutableListOf<CompletableDeferred<ClientList>>();val profiles=mutableListOf<CompletableDeferred<ClientProfile>>()
        var listProblem: ReadProblem?=null;var searchProblem: ReadProblem?=null
        override suspend fun clients(business: Int): ClientList {
            requests+=ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "$business","limit" to "50"))
            listProblem?.let {throw ReadException(it)};return JsonContracts.clients(fixture("clients-$business"))
        }
        override suspend fun searchClients(business: Int,search: String): ClientList {
            requests+=ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "$business","limit" to "50","search" to search))
            searchProblem?.let {throw ReadException(it)}
            return if(holdSearch)CompletableDeferred<ClientList>().also {searches+=it}.await() else page(business,search)
        }
        override suspend fun clientProfile(business: Int,id: Int): ClientProfile {
            requests+=ReadRequest("/api/mobile/v1/clients/$id/",mapOf("business" to "$business"))
            return if(holdProfile)CompletableDeferred<ClientProfile>().also {profiles+=it}.await() else JsonContracts.clientProfile(FixtureClientSearch.profile(fixture("client-search-catalogue-$business"),business,id).body)
        }
    }
    @Test fun queryProducerSearchesBeyondLoadedAndFirst50WindowIncludingSourceOnlyMatches() {
        val initial=JsonContracts.clients(fixture("clients-101"));val all=page(101,"Synthetic");val beyond=page(101,"Beyond");val notes=page(101,"fixture-note-tag")
        assertFalse(initial.items.any {it.id==1701});assertFalse(all.items.any {it.id==1701});assertEquals(50,all.items.size);assertEquals(56,all.total)
        assertEquals(listOf(1701),beyond.items.map {it.id});assertEquals(listOf(1702),notes.items.map {it.id})
        assertEquals(listOf(2701),page(202,"Beyond").items.map {it.id})
    }
    @Test fun sourceCountsEmptyAndPartialRemainDifferentWithoutLocalRefilter() {
        val s=ClientSearchSession();assertFalse(s.open(a));s.bind(a);s.open(a);val token=s.state.selection!!
        assertFalse(s.state.showsEmpty);s.update("fixture-note-tag",token);s.accept(page(101,"fixture-note-tag"),s.begin(token)!!)
        assertEquals(listOf(1702),s.state.items.map {it.id});assertTrue(s.select(1702,token));val oldProfile=s.state.profileSelection!!;s.select(1702,token);val newProfile=s.state.profileSelection!!;s.backProfile(token,oldProfile);assertEquals(newProfile,s.state.profileSelection);s.backProfile(token,newProfile);assertEquals("fixture-note-tag",s.state.query)
        s.update("Synthetic",token);s.accept(page(101,"Synthetic"),s.begin(token)!!);assertTrue(s.state.partial);assertEquals(56,s.state.total)
        s.update("does-not-exist",token);s.accept(page(101,"does-not-exist"),s.begin(token)!!);assertTrue(s.state.showsEmpty)
        s.accept(ClientList(101,emptyList(),3),s.begin(token)!!);assertTrue(s.state.partial);assertFalse(s.state.showsEmpty)
    }
    @Test fun rawInputRetryClearCloseAndLateCallbacksNeverReuseOldQueryResults() {
        val s=ClientSearchSession();s.bind(a);s.open(a);val old=s.state.selection!!;s.update("\u001C Beyond \n",old);val pending=s.begin(old)!!
        assertEquals("Beyond",pending.query);assertEquals("\u001C Beyond \n",s.state.query)
        s.update("new query",old);s.accept(page(101,"Beyond"),pending);s.fail(ReadProblem.DENIED,pending);assertFalse(s.state.loaded);assertNull(s.state.problem)
        s.fail(ReadProblem.UNAVAILABLE,s.begin(old)!!);assertEquals("new query",s.state.query);assertFalse(s.state.showsEmpty)
        s.clear(old);assertEquals("",s.state.query);assertNull(s.state.problem);assertFalse(s.state.loaded)
        s.update("Beyond",old);val closing=s.begin(old)!!;s.close(old);s.open(a);val fresh=s.state.selection!!
        s.update("old",old);s.clear(old);s.close(old);s.accept(page(101,"Beyond"),closing)
        assertNotEquals(old,fresh);assertEquals(fresh,s.state.selection);assertEquals("Beyond",s.state.query);assertFalse(s.state.loaded)
    }
    @Test fun malformedResultsForeignContextAndUnknownIDAreRejected() {
        val s=ClientSearchSession();s.bind(a);s.open(a);val token=s.state.selection!!;val good=page(101,"Beyond");val row=good.items.single()
        for(bad in listOf(good.copy(business=202),good.copy(items=listOf(row,row),total=2),good.copy(items=listOf(row.copy(id=0))),good.copy(total=0),good.copy(items=(1..51).map {row.copy(id=it)},total=51))) {
            assertFalse(s.accept(bad,s.begin(token)!!));assertEquals(ReadProblem.INVALID_PAYLOAD,s.state.problem);assertTrue(s.state.items.isEmpty());assertFalse(s.state.showsEmpty)
        }
        s.accept(good,s.begin(token)!!);assertFalse(s.select(701,token))
        val pending=s.begin(token)!!;s.bind(ClientSearchContext(202,21));s.accept(good,pending);assertNull(s.state.selection);assertEquals("",s.state.query)
        s.bind(ClientSearchContext(0,0));assertNull(s.state.context)
    }
    @Test fun existingQueryParameterIsEncodedWithoutChangingBusinessOrPath()=runTest {
        val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {read->requests+=read;FixtureClientSearch.list(fixture("client-search-catalogue-101"),101,read.query["search"] ?: "")})
        val raw="+700 &business=202/测试?x=1#fragment";repo.searchClients(101,"\u001C$raw\n")
        val read=requests.single();assertEquals(mapOf("business" to "101","limit" to "50","search" to raw),read.query)
        val uri=NativeRequestBuilder(java.net.URI("https://fixtures.invalid"),30000).request(read).uri
        val parts=uri.rawQuery.split('&').associate {part->val pair=part.split('=',limit=2);java.net.URLDecoder.decode(pair[0],"UTF-8") to java.net.URLDecoder.decode(pair[1],"UTF-8")}
        assertEquals("/api/mobile/v1/clients/",uri.path);assertEquals(raw,parts["search"]);assertEquals("101",parts["business"]);assertEquals(3,parts.size)
    }
    @Test fun ownerSearchProfileBackPreservesDirectoryAndDoesNotCreateContactsOrReuseProjection()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repository();val parent=ClientDirectoryViewModel(repo)
        try {
            parent.load(101,20);runCurrent();parent.search("Alpha");val rows=parent.state.items;val child=parent.serverSearch!!;val before=repo.requests.size
            child.open(a);val token=child.state.selection!!;assertEquals(before,repo.requests.size)
            child.update("  Beyond  ",token);child.submit(token);runCurrent();assertEquals(listOf(1701),child.state.items.map {it.id});assertEquals("Beyond",repo.requests.last().query["search"])
            val beforeProfile=repo.requests.size;child.openClient(1701,token);runCurrent();assertEquals(beforeProfile+1,repo.requests.size);assertEquals("/api/mobile/v1/clients/1701/",repo.requests.last().path);assertEquals(1701,child.profile.state.detail?.client?.id)
            val oldProfile=child.state.profileSelection!!;child.openClient(1701,token);runCurrent();val newProfile=child.state.profileSelection!!;val beforeStale=repo.requests.size
            child.backProfile(token,oldProfile);child.retryProfile(token,oldProfile);runCurrent();assertEquals(newProfile,child.state.profileSelection);assertEquals(beforeStale,repo.requests.size)
            child.backProfile(token,newProfile);assertNull(child.profile.state.detail);assertEquals("  Beyond  ",child.state.query);assertEquals(listOf(1701),child.state.items.map {it.id})
            assertEquals(rows,parent.state.items);assertEquals("Alpha",parent.state.query);assertNull(parent.state.selectedID)
            val invalid=repo.requests.size;child.openClient(701,token);runCurrent();assertEquals(invalid,repo.requests.size)
            child.clear(token);assertEquals(invalid,repo.requests.size);assertFalse(child.state.loaded);assertFalse(child.state.showsEmpty)
        } finally {parent.back();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pendingQueryClearReopenBusinessAndLateProfileAreScopeIsolated()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repository();val parent=ClientDirectoryViewModel(repo)
        try {
            parent.load(101,20);runCurrent();val child=parent.serverSearch!!;child.open(a);val old=child.state.selection!!;child.update("Beyond",old)
            repo.holdSearch=true;child.submit(old);runCurrent();child.clear(old);repo.searches[0].complete(page(101,"Beyond"));runCurrent();assertFalse(child.state.loaded)
            child.update("Beyond",old);child.submit(old);runCurrent();child.close(old);child.open(a);val fresh=child.state.selection!!;repo.searches[1].complete(page(101,"Beyond"));runCurrent();assertFalse(child.state.loaded)
            child.submit(fresh);runCurrent();parent.load(202,21);assertEquals("",child.state.query);assertNull(child.state.selection);runCurrent();repo.searches[2].complete(page(101,"Beyond"));runCurrent();assertTrue(child.state.items.isEmpty())
            repo.holdSearch=false;child.open(ClientSearchContext(202,21));val b=child.state.selection!!;child.update("Beyond",b);child.submit(b);runCurrent();assertEquals(listOf(2701),child.state.items.map {it.id})
            repo.holdProfile=true;child.openClient(2701,b);runCurrent();parent.load(101,22);runCurrent()
            repo.profiles[0].complete(JsonContracts.clientProfile(FixtureClientSearch.profile(fixture("client-search-catalogue-202"),202,2701).body));runCurrent();assertNull(child.profile.state.detail);assertNull(child.profile.state.id);assertNull(child.state.selection)
        } finally {parent.back();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun recoverableSearchAndParentErrorsRetainInputButDeniedParentInvalidatesOwner()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repository();val parent=ClientDirectoryViewModel(repo)
        try {
            parent.load(101,20);runCurrent();val child=parent.serverSearch!!;child.open(a);val token=child.state.selection!!;child.update("Recoverable",token)
            repo.searchProblem=ReadProblem.UNAVAILABLE;child.submit(token);runCurrent();assertEquals("Recoverable",child.state.query);assertEquals(ReadProblem.UNAVAILABLE,child.state.problem);assertFalse(child.state.showsEmpty)
            repo.listProblem=ReadProblem.UNAVAILABLE;parent.load(101,20);runCurrent();assertEquals(token,child.state.selection);assertEquals("Recoverable",child.state.query)
            repo.listProblem=ReadProblem.DENIED;parent.load(101,20);runCurrent();assertNull(child.state.selection);assertNull(child.state.context);assertEquals("",child.state.query)
        } finally {parent.back();parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
