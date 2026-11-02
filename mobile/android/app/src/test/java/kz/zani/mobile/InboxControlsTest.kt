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
class InboxControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(b:Int)=JsonContracts.inbox(fixture("inbox-$b"))
    private class Controlled:InboxRepository {
        val pages=mutableListOf<CompletableDeferred<InboxList>>();val threads=mutableListOf<CompletableDeferred<InboxThread>>()
        override suspend fun inbox(business:Int)=CompletableDeferred<InboxList>().also {pages+=it}.await()
        override suspend fun thread(business:Int,id:Int)=CompletableDeferred<InboxThread>().also {threads+=it}.await()
    }
    private fun controlled(block:suspend TestScope.(InboxViewModel,Controlled)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Controlled();val m=InboxViewModel(repo)
        try {block(m,repo)} finally {m.back();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    private fun ready(block:suspend TestScope.(InboxViewModel,MutableList<ReadRequest>)->Unit)=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {q->requests+=q;val b=q.query["business"];val id=q.path.trimEnd('/').substringAfterLast('/');val name=when {q.path.endsWith("/inbox/")->"inbox-$b";q.path.contains("/inbox/")->"inbox-$b-$id";else->"client-$b-$id"};ReadResponse(200,fixture(name))});val m=InboxViewModel(repo)
        try {m.load(101,1);runCurrent();m.open(901,m.control);runCurrent();block(m,requests)} finally {m.back();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun currentFiltersVisibleRowsAndOldPendingCallbacksDoNotIssueExtraReads()=controlled {m,r->
        assertNull(m.control);assertFalse(m.matches(null));m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();val list=m.control!!
        m.search("Alpha",list);m.filterUnread(true,false,list);m.filterUnread(false,false,list);assertTrue(m.state.unreadOnly);assertEquals(listOf(901),m.state.visible.map {it.id})
        m.open(902,list);m.open(999,list);runCurrent();assertEquals(0,r.threads.size);m.open(901,list);runCurrent();val pending=m.control!!
        m.search("old",list);m.filterUnread(false,true,list);m.retryList(list);m.open(901,list);runCurrent();assertEquals(1,r.pages.size);assertEquals(1,r.threads.size);assertEquals(pending,m.control);assertEquals("Alpha",m.state.query);assertTrue(m.state.unreadOnly)
        r.threads[0].complete(JsonContracts.thread(fixture("inbox-101-901")));runCurrent();m.back(m.control,m.threadSelection);assertNull(m.state.selectedID);assertEquals("Alpha",m.state.query);m.open(901,list);runCurrent();assertEquals(1,r.threads.size)
    }
    @Test fun listRetryGenerationEpochAndForeignOwnerQuarantineOldFiltersAndRows()=controlled {m,r->
        m.load(101,1);runCurrent();r.pages[0].complete(page(101));runCurrent();val old=m.control!!;m.search("Alpha",old);m.retryList(old);runCurrent();val pending=m.control!!
        m.retryList(pending);m.search("old",old);runCurrent();assertEquals(2,r.pages.size);assertEquals("Alpha",m.state.query);r.pages[1].complete(page(101));runCurrent();m.retryList(old);runCurrent();assertEquals(2,r.pages.size)
        m.load(101,2);runCurrent();r.pages[2].complete(page(101));runCurrent();val epoch=m.control!!;m.search("Current",epoch);m.search("leak",pending);m.filterUnread(true,false,pending);m.open(901,pending);m.retryList(pending);runCurrent();assertEquals("Current",m.state.query);assertFalse(m.state.unreadOnly);assertTrue(r.threads.isEmpty())
        m.load(202,3);runCurrent();r.pages[3].complete(page(202));runCurrent();m.search("leak",epoch);m.retryList(epoch);m.open(901,epoch);runCurrent();assertEquals(listOf(951),m.state.items.map {it.id});assertEquals("",m.state.query);assertEquals(4,r.pages.size);assertTrue(r.threads.isEmpty())
        m.reconcileHandoffOwner(202,4);m.retryList(epoch);runCurrent();assertNull(m.control);assertNull(m.state.business);assertEquals(4,r.pages.size)
    }
    @Test fun replyEntryOldBackAndRetryCannotResetCurrentOrReopenedPrivateDraft()=ready {m,requests->
        val entry=m.control!!;val target=m.threadSelection!!;val c=m.reply.state.context!!;val reads=requests.size;m.openReply(c,entry);val draft=m.reply.state.selection!!;val active=m.control!!;m.reply.update("Private",draft)
        m.openReply(c,entry);m.back(entry,target);m.retryThread(target,entry);runCurrent();assertEquals(reads,requests.size);assertEquals(draft,m.reply.state.selection);assertEquals("Private",m.reply.state.text)
        m.openReply(c,active);assertEquals(draft,m.reply.state.selection);m.reply.close(draft);m.openReply(c,active);val reopened=m.reply.state.selection!!;assertNotEquals(draft,reopened);assertEquals("Private",m.reply.state.text)
        m.back(active,target);assertEquals(reopened,m.reply.state.selection);m.back(m.control,m.threadSelection);assertNull(m.state.selectedID)
    }
    @Test fun inspectorSameParentReopenRejectsOldPresentationBackRetryAndEntry()=ready {m,requests->
        val links=m.clientLinks!!;val entry=m.control!!;val idle=links.presentation!!;val before=requests.size;m.openClient(idle,entry);runCurrent();val first=links.presentation!!;val parent=m.control!!
        assertEquals(701,links.profile.state.detail!!.client.id);assertEquals(before+2,requests.size);assertEquals(idle.request,first.request);assertNotEquals(idle,first)
        links.open(presentation=idle);assertFalse(links.back(presentation=idle));runCurrent();assertEquals(before+2,requests.size);assertTrue(links.back(presentation=first));val closed=links.presentation!!
        m.openClient(closed,parent);runCurrent();val second=links.presentation!!;val reads=requests.size;links.open(presentation=first);m.openClient(closed,parent);assertFalse(links.back(presentation=first));runCurrent()
        assertEquals(first.request,second.request);assertNotEquals(first,second);assertEquals(reads,requests.size);assertEquals(second,links.presentation);assertNotNull(links.profile.state.detail)
    }
    @Test fun currentInspectorAndDraftCannotBeDisplacedByOldCrossEntryOrNewEpoch()=ready {m,requests->
        val links=m.clientLinks!!;val entry=m.control!!;m.openClient(links.presentation,entry);runCurrent();val p=links.presentation!!;val owner=m.control!!;val context=m.reply.state.context!!
        m.openReply(context,owner);assertNull(m.reply.state.selection);assertEquals(p,links.presentation);assertTrue(links.back(presentation=p));m.openReply(context,owner);val draft=m.reply.state.selection!!;m.reply.update("Private",draft)
        val reads=requests.size;m.openClient(links.presentation,owner);runCurrent();assertEquals(draft,m.reply.state.selection);assertEquals("Private",m.reply.state.text);assertNull(links.state.selectedID);assertEquals(reads,requests.size)
        m.reconcileHandoffOwner(101,2);links.open(presentation=p);m.openClient(p,owner);runCurrent();assertEquals(reads,requests.size);assertNull(links.presentation);assertNull(m.state.thread);assertNull(m.reply.state.context)
    }
}
