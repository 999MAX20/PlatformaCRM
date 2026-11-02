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
class InboxListThreadControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private inner class Repo:InboxClientRepository {
        var holdLists=false;var holdThreads=false;var listFailure:ReadProblem?=null;var threadFailure:ReadProblem?=null;var partial=false
        val reads=mutableListOf<Triple<String,Int,Int>>();val lists=mutableListOf<CompletableDeferred<InboxList>>();val threads=mutableListOf<CompletableDeferred<InboxThread>>()
        override suspend fun inbox(business:Int):InboxList {reads+=Triple("list",business,0);listFailure?.let {listFailure=null;throw ReadException(it)};return if(holdLists)CompletableDeferred<InboxList>().also {lists+=it}.await() else JsonContracts.inbox(fixture("inbox-$business")).let {if(partial)it.copy(total=it.total+1) else it}}
        override suspend fun thread(business:Int,id:Int):InboxThread {reads+=Triple("thread",business,id);threadFailure?.let {threadFailure=null;throw ReadException(it)};return if(holdThreads)CompletableDeferred<InboxThread>().also {threads+=it}.await() else JsonContracts.thread(fixture("inbox-$business-$id"))}
        override suspend fun clientProfile(business:Int,id:Int):ClientProfile {reads+=Triple("client",business,id);return JsonContracts.clientProfile(fixture("client-$business-$id"))}
    }
    private suspend fun TestScope.withModel(block:suspend TestScope.(Repo,InboxViewModel)->Unit) {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val model=InboxViewModel(repo)
        try {model.load(101,120);runCurrent();block(repo,model)} finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun continuousTypingRetainsInputButRevokesQueryWindowRowAndRetryAfterABA()=runTest {withModel {repo,model->
        val input=model.listInputControl!!;val initial=model.listControl!!;val count=repo.reads.size
        model.searchInput("res",input);model.searchInput("response",input);assertEquals(input,model.listInputControl);assertEquals(listOf(901),model.state.visible.map {it.id})
        val row=model.listControl!!;model.searchInput("Synthetic",input);model.searchInput("response",input);model.openList(901,row);model.retryListWindow(initial);runCurrent()
        assertEquals(count,repo.reads.size);assertNull(model.state.selectedID);assertEquals("response",model.state.query)
    }}
    @Test fun unreadFilterABAAndRawSetterChangesCannotReviveOldAction()=runTest {withModel {repo,model->
        val input=model.listInputControl!!;val old=model.listControl!!;model.filterUnreadList(true,old);model.filterUnreadList(false,model.listControl);model.filterUnreadList(true,old)
        assertFalse(model.state.unreadOnly);assertEquals(input,model.listInputControl);val before=repo.reads.size
        model.search("Alpha");model.search("");model.openList(901,old);model.retryListWindow(old);runCurrent();assertEquals(before,repo.reads.size);assertNull(model.state.selectedID)
    }}
    @Test fun filteredOutRowsAndPartialNoMatchesRespectBoundedSourceWithoutRequests()=runTest {withModel {repo,model->
        val before=repo.reads.size;model.filterUnreadList(true,model.listControl);model.openList(902,model.listControl);runCurrent();assertNull(model.state.selectedID);assertEquals(listOf(901),model.state.visible.map {it.id});assertEquals(before,repo.reads.size)
        repo.partial=true;model.retryListWindow(model.listControl);runCurrent();val reads=repo.reads.size;model.searchInput("absent",model.listInputControl);assertTrue(model.state.partial);assertTrue(model.state.visible.isEmpty());assertFalse(model.state.showsEmpty);assertEquals(reads,repo.reads.size)
    }}
    @Test fun pendingListBlocksDuplicateRetryRowAndOldInputThenKeepsOwnFilter()=runTest {withModel {repo,model->
        val input=model.listInputControl!!;model.searchInput("response",input);val list=model.listControl!!;val before=repo.reads.size;repo.holdLists=true
        model.retryListWindow(list);runCurrent();assertNull(model.listControl);assertNull(model.listInputControl)
        model.searchInput("late",input);model.retryListWindow(list);model.openList(901,list);runCurrent();assertEquals(before+1,repo.reads.size);assertEquals("response",model.state.query)
        repo.lists[0].complete(JsonContracts.inbox(fixture("inbox-101")));runCurrent();assertNotEquals(input,model.listInputControl);assertEquals("response",model.state.query);assertEquals(listOf(901),model.state.visible.map {it.id})
    }}
    @Test fun failedListAllowsContinuousInputButOnlyCurrentWindowCanRetry()=runTest {withModel {repo,model->
        repo.listFailure=ReadProblem.DENIED;model.retryListWindow(model.listControl);runCurrent();val old=model.listControl!!;val input=model.listInputControl!!;val before=repo.reads.size
        model.searchInput("Beta",input);model.retryListWindow(old);runCurrent();assertEquals(before,repo.reads.size);assertEquals(ReadProblem.DENIED,model.state.problem);assertNull(model.state.selectedID)
        model.retryListWindow(model.listControl);runCurrent();assertNull(model.state.problem);assertEquals("Beta",model.state.query);assertEquals(listOf(902),model.state.visible.map {it.id})
    }}
    @Test fun threadRetryExistsOnlyForCurrentFailureAndRejectsPendingOrSuccessfulReads()=runTest {withModel {repo,model->
        repo.threadFailure=ReadProblem.DENIED;model.openList(901,model.listControl);runCurrent();val retry=model.threadRetryControl!!;assertNull(model.listControl)
        repo.holdThreads=true;model.retryThreadWindow(retry);runCurrent();val count=repo.reads.size;assertTrue(model.state.threadLoading);assertNull(model.threadRetryControl)
        model.retryThreadWindow(retry);model.retryThreadWindow(model.threadRetryControl);runCurrent();assertEquals(count,repo.reads.size)
        repo.threads[0].complete(JsonContracts.thread(fixture("inbox-101-901")));runCurrent();model.retryThreadWindow(retry);runCurrent();assertEquals(count,repo.reads.size);assertEquals(901,model.state.thread?.conversation?.id);assertNull(model.threadRetryControl)
    }}
    @Test fun staleListAndFailureControlsCannotTouchReplyInspectorOrNewEpoch()=runTest {withModel {repo,model->
        val input=model.listInputControl!!;val list=model.listControl!!;repo.threadFailure=ReadProblem.DENIED;model.openList(901,list);runCurrent();val retry=model.threadRetryControl!!;model.retryThreadWindow(retry);runCurrent()
        val context=ReplyDraftContext(101,901,120);model.openReply(context,model.control);model.reply.update("Private retained",model.reply.inputControl);val before=repo.reads.size
        model.searchInput("hidden",input);model.retryThreadWindow(retry);model.retryListWindow(list);runCurrent();assertEquals(before,repo.reads.size);assertEquals("Private retained",model.reply.state.text);assertEquals("",model.state.query);assertNull(model.listControl)
        model.reply.close(expected=model.reply.returnControl);model.openClientEntry(model.clientLinks!!.entryControl,model.control);runCurrent();val inspector=repo.reads.size
        model.retryThreadWindow(retry);model.openList(902,list);runCurrent();assertEquals(inspector,repo.reads.size);assertEquals(701,model.clientLinks!!.state.selectedID)
        model.load(101,121);runCurrent();model.searchInput("old",input);model.openList(901,list);runCurrent();assertEquals(121,model.state.scopeEpoch);assertNull(model.state.selectedID);assertEquals("",model.state.query)
    }}
    @Test fun lateOldDetailFailureCannotInstallRetryForReplacementBusiness()=runTest {withModel {repo,model->
        repo.holdThreads=true;model.openList(901,model.listControl);runCurrent();model.load(202,122);runCurrent();val current=model.listControl
        repo.threads[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(202,model.state.business);assertEquals(current,model.listControl);assertNull(model.state.selectedID);assertNull(model.state.threadProblem);assertNull(model.threadRetryControl)
    }}
    @Test fun sharedRawUnicodeInboxInputRevokesOnlyChangedWindowAndPreservesSourceUnreadAndEpochOwnership()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val cases=org.json.JSONObject(fixture("inbox-list-raw-unicode-cases")).getJSONArray("cases")
            for(i in 0 until cases.length()) {
                val row=cases.getJSONObject(i);val page=JsonContracts.inbox(row.getString("list_json"));val reads=mutableListOf<String>();val repo=object:InboxRepository {override suspend fun inbox(business:Int):InboxList {reads+="list:$business";return page};override suspend fun thread(business:Int,id:Int):InboxThread {reads+="thread:$business:$id";return JsonContracts.thread(fixture("inbox-$business-$id"))}}
                val m=InboxViewModel(repo)
                try {
                    val epoch=1900+i;m.load(101,epoch);runCurrent();val input=m.listInputControl!!;m.searchInput(row.getString("before"),input);val old=m.listControl!!;m.searchInput(row.getString("after"),input);val current=m.listControl!!;val changed=row.getBoolean("changed");val partial=row.getBoolean("partial")
                    assertEquals(row.getString("after"),m.state.query);assertEquals(input,m.listInputControl);assertEquals(changed,old!=current);assertEquals(listOf(901),m.state.visible.map {it.id});val before=reads.toList()
                    if(changed){m.filterUnreadList(true,old);m.openList(901,old);m.retryListWindow(old);runCurrent()};assertEquals(before,reads);assertFalse(m.state.unreadOnly);assertNull(m.state.selectedID);assertEquals(page.items,m.state.items);assertEquals(page.total,m.state.total);assertEquals(partial,m.state.partial)
                    val filter=m.listControl!!;m.filterUnreadList(true,filter);m.filterUnreadList(false,filter);assertTrue(m.state.unreadOnly);assertEquals(input,m.listInputControl);m.filterUnreadList(false,m.listControl);assertFalse(m.state.unreadOnly)
                    m.openList(901,m.listControl);runCurrent();assertEquals(901,m.state.thread!!.conversation.id);assertNull(m.listInputControl);val detail=JsonContracts.thread(fixture("inbox-101-901"));val expectedReadItems=page.items.map {if(it.id==901)detail.conversation else it};assertEquals(expectedReadItems,m.state.items);val openedItems=m.state.items.toList();m.searchInput("hidden overwrite",input);assertEquals(row.getString("after"),m.state.query);m.backToThreadList(m.returnControl);val back=m.listInputControl!!;m.searchInput("old input",input);assertNotEquals(input,back);assertEquals(row.getString("after"),m.state.query);assertEquals(openedItems,m.state.items)
                    m.searchInput("__absent_unicode_window_fixture__",back);assertTrue(m.state.visible.isEmpty());assertEquals(!partial,m.state.showsEmpty);val priorInput=m.listInputControl!!;m.retryListWindow(m.listControl);runCurrent();assertEquals("__absent_unicode_window_fixture__",m.state.query);assertNotEquals(priorInput,m.listInputControl);assertEquals(page.items,m.state.items);assertEquals(partial,m.state.partial)
                    val prior=m.listInputControl!!;val window=m.listControl!!;m.load(101,epoch+100);runCurrent();val count=reads.size;m.searchInput("old epoch",prior);m.filterUnreadList(true,window);m.openList(901,window);m.retryListWindow(window);runCurrent();assertTrue(m.state.query.isEmpty());assertFalse(m.state.unreadOnly);assertNull(m.state.selectedID);assertEquals(count,reads.size)
                } finally {m.viewModelScope.cancel()}
            }
        } finally {Dispatchers.resetMain()}
    }
}
