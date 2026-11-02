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
class ClientDirectoryControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private class Controlled:ClientRepository {
        val pending=mutableListOf<CompletableDeferred<ClientList>>()
        override suspend fun clients(business:Int):ClientList=CompletableDeferred<ClientList>().also {pending+=it}.await()
    }
    private fun check(block:suspend TestScope.(ClientDirectoryViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();val model=ClientDirectoryViewModel(repo)
        try {block(model,repo)} finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private fun page(b:Int)=JsonContracts.clients(fixture("clients-$b"))
    @Test fun currentRowsBackAndContactEchoRetainQueryCountAndRejectOldNavigation()=check {m,r->
        assertNull(m.control);assertFalse(m.matches(null));m.load(101,1);runCurrent();r.pending[0].complete(page(101));runCurrent()
        val list=m.control!!;m.search("Alpha",list);assertEquals(listOf(701),m.state.visible.map {it.id});assertFalse(m.open(702,list));assertFalse(m.open(999,list));assertTrue(m.open(701,list))
        val first=m.control!!;m.search("overwrite",list);assertFalse(m.back(list));assertEquals("Alpha",m.state.query)
        val old=m.state.items[0];val fresh=old.copy(title="Fresh",phone=null,email=null)
        m.refreshContact(202,fresh,first);assertEquals(old,m.state.items[0]);m.refreshContact(101,fresh,first);assertEquals(fresh,m.state.items[0]);assertEquals(first,m.control);assertEquals(2,m.state.total)
        assertTrue(m.back(first));val returned=m.control!!;assertNotEquals(list,returned);assertFalse(m.open(701,list));m.search("",returned);assertTrue(m.open(702,returned));val second=m.control
        m.refreshContact(101,old,first);assertEquals(fresh,m.state.items[0]);assertFalse(m.back(first));assertEquals(second,m.control);assertEquals(1,r.pending.size)
    }
    @Test fun readGenerationPendingAndSameBusinessEpochRejectOldQueryRowRetryAndEntry()=check {m,r->
        m.load(101,1);runCurrent();r.pending[0].complete(page(101));runCurrent();val old=m.control!!
        m.retry(old);runCurrent();val pending=m.control!!;m.retry(pending);m.search("old",old);assertFalse(m.openDraft(pending));assertEquals(2,r.pending.size);assertEquals("",m.state.query)
        r.pending[1].complete(page(101));runCurrent();m.retry(old);runCurrent();assertEquals(2,r.pending.size);assertEquals(pending,m.control)
        m.load(101,2);runCurrent();r.pending[2].complete(page(101));runCurrent();val current=m.control!!;m.search("Beta",current)
        m.search("leak",pending);m.retry(pending);assertFalse(m.back(pending));assertFalse(m.open(701,pending));assertFalse(m.openDraft(pending));runCurrent();assertEquals(3,r.pending.size);assertEquals(current,m.control);assertEquals("Beta",m.state.query)
    }
    @Test fun foreignAndClearedOwnerControlsNeverReadOrExposeOtherBusiness()=check {m,r->
        m.load(101,1);runCurrent();r.pending[0].complete(page(101));runCurrent();val old=m.control!!
        m.load(202,2);runCurrent();r.pending[1].complete(page(202));runCurrent();val current=m.control!!;m.search("Current",current)
        m.search("leak",old);m.retry(old);m.refreshContact(101,page(101).items[0],old);assertFalse(m.back(old));assertFalse(m.open(701,old));assertFalse(m.openDraft(old));runCurrent()
        assertEquals(2,r.pending.size);assertEquals(202,m.state.business);assertEquals(page(202).items,m.state.items);assertEquals("Current",m.state.query)
        m.reconcileOwner(202,3);m.retry(current);runCurrent();assertNull(m.control);assertNull(m.state.business);assertEquals(2,r.pending.size)
    }
    @Test fun currentCreateSearchEntryDoesNotRequestAndOldEntryCannotClosePrivateDraft()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));var reads=0
        val repo=APIReadRepository(ReadTransport {reads++;ReadResponse(200,fixture("clients-101"))});val m=ClientDirectoryViewModel(repo)
        try {
            m.load(101,1);runCurrent();val entry=m.control!!;assertTrue(m.openDraft(entry));val draft=m.draft.state.selection!!;m.draft.update(ClientDraftField.FULL_NAME,"Retained private",draft);val ownDraft=m.control!!
            assertFalse(m.openSearch(entry));assertFalse(m.back(entry));assertFalse(m.openDraft(entry));assertEquals(draft,m.draft.state.selection);assertEquals("Retained private",m.draft.state.values.fullName)
            assertTrue(m.openSearch(ownDraft));assertNull(m.draft.state.selection);val search=m.serverSearch!!.state.selection!!;val ownSearch=m.control!!
            assertFalse(m.back(ownDraft));assertEquals(search,m.serverSearch.state.selection);assertTrue(m.back(ownSearch));assertEquals(1,reads)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun profileRetryCapturedReadGenerationEpochPendingAndClearCannotResurrect()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val replies=mutableListOf<CompletableDeferred<ClientProfile>>();var callbacks=0
        val m=ClientProfileViewModel(object:ClientProfileRepository {override suspend fun clientProfile(business:Int,id:Int)=CompletableDeferred<ClientProfile>().also {replies+=it}.await()},ownerScope=backgroundScope)
        try {
            m.loadScoped(101,701,1);runCurrent();val first=m.readSelection!!;m.retry(first,1);runCurrent();assertEquals(1,replies.size)
            replies[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));runCurrent();m.retry(first,1) {_,_->callbacks++};runCurrent();val second=m.readSelection!!;m.retry(first,1);runCurrent();assertEquals(2,replies.size)
            replies[1].complete(JsonContracts.clientProfile(fixture("client-101-701")));runCurrent();assertNotNull(m.state.detail);assertEquals(1,callbacks);assertNotEquals(first,second)
            m.retry(first,1);m.retry(second,2);runCurrent();assertEquals(2,replies.size);assertEquals(second,m.readSelection)
            m.clear();m.retry(second,1);runCurrent();assertNull(m.readSelection);assertNull(m.state.detail);assertEquals(2,replies.size);assertEquals(1,callbacks)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
