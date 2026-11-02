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
class InboxClientControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun thread(b:Int=101,id:Int=901)=JsonContracts.thread(fixture("inbox-$b-$id"))
    private val first=InboxReadSelection(101,901,1);private val second=InboxReadSelection(202,951,2)
    private inner class Repo:InboxClientRepository,ClientWorkRepository {
        var hold=false;var failure:ReadProblem?=null;var fresh:InboxThread?=null
        val requests=mutableListOf<Triple<String,Int,Int>>();val threads=mutableListOf<CompletableDeferred<InboxThread>>();val profiles=mutableListOf<CompletableDeferred<ClientProfile>>()
        override suspend fun inbox(business:Int):InboxList {requests+=Triple("list",business,0);return JsonContracts.inbox(fixture("inbox-$business"))}
        override suspend fun thread(business:Int,id:Int):InboxThread {requests+=Triple("thread",business,id);failure?.let {throw ReadException(it)};return if(hold)CompletableDeferred<InboxThread>().also {threads+=it}.await() else fresh ?: this@InboxClientControlsTest.thread(business,id)}
        override suspend fun clientProfile(business:Int,id:Int):ClientProfile {requests+=Triple("client",business,id);return if(hold)CompletableDeferred<ClientProfile>().also {profiles+=it}.await() else JsonContracts.clientProfile(fixture("client-$business-$id"))}
        override suspend fun taskDetails(business:Int,id:Int):TaskDetails {requests+=Triple("task",business,id);return JsonContracts.taskDetails(fixture("task-$business-$id"))}
        override suspend fun appointment(business:Int,id:Int)=JsonContracts.detail(fixture("appointment-$business-$id"))
    }
    @Test fun successCallbackOwnerRebindCannotStartOldClientOrNotifyNewCallback()=runTest {
        val repo=Repo();val links=InboxClientModel(repo,backgroundScope);var firstCalls=0;var newCalls=0
        links.bind(thread(),first) {_,_->firstCalls++;links.bind(thread(202,951),second) {_,_->newCalls++}}
        links.openEntry(links.entryControl);runCurrent()
        assertEquals(listOf(Triple("thread",101,901)),repo.requests);assertEquals(1,firstCalls);assertEquals(0,newCalls);assertEquals(second,links.state.request);assertEquals(801,links.state.parent?.clientReferenceID);assertNull(links.state.selectedID);assertNull(links.profile.state.detail);assertNotNull(links.entryControl)
    }
    @Test fun failureCallbackRebindCannotEraseReplacementParentOrProfile()=runTest {
        val repo=Repo();repo.failure=ReadProblem.DENIED;val links=InboxClientModel(repo,backgroundScope)
        links.bind(thread(),first) {_,problem->assertEquals(ReadProblem.DENIED,problem);links.bind(thread(202,951),second) {_,_->}}
        links.openEntry(links.entryControl);runCurrent()
        assertEquals(second,links.state.request);assertEquals(801,links.state.parent?.clientReferenceID);assertNotNull(links.entryControl);assertNull(links.profile.state.detail);assertEquals(1,repo.requests.size)
    }
    @Test fun callbackCloseAndSameRequestRebindStopDependentRead()=runTest {
        for(rebind in listOf(false,true)) {
            val repo=Repo();val links=InboxClientModel(repo,backgroundScope)
            links.bind(thread(),first) {_,_->if(rebind)links.bind(thread(),first) {_,_->} else links.closeInspector(links.returnControl)}
            links.openEntry(links.entryControl);runCurrent();assertEquals(1,repo.requests.size);assertNull(links.state.selectedID);assertNull(links.profile.state.detail);assertFalse(links.state.loading)
        }
    }
    @Test fun duplicatePendingEntryRetryAndProfileLoadingNeverRestartReads()=runTest {
        val repo=Repo();repo.hold=true;val links=InboxClientModel(repo,backgroundScope);links.bind(thread(),first) {_,_->};val entry=links.entryControl!!
        links.openEntry(entry);runCurrent();val pending=links.control!!;links.openEntry(entry);links.retry(pending);runCurrent();assertEquals(1,repo.requests.size)
        repo.threads[0].complete(thread());runCurrent();val profilePending=links.control!!;links.retry(profilePending);runCurrent()
        assertNotNull(profilePending.profile);assertTrue(profilePending.profileLoading);assertNotEquals(pending,profilePending);assertEquals(2,repo.requests.size)
        repo.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertEquals(ReadProblem.DENIED,links.profile.state.problem);assertFalse(links.state.loading)
    }
    @Test fun retryUsesFreshThreadAndActualIndependentProfileReadForSameClient()=runTest {
        val repo=Repo();repo.hold=true;val links=InboxClientModel(repo,backgroundScope);links.bind(thread(),first) {_,_->};links.openEntry(links.entryControl);runCurrent();val early=links.returnControl!!
        repo.threads[0].complete(thread());runCurrent();repo.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();val denied=links.control!!;val deniedReturn=links.returnControl!!
        assertFalse(links.closeInspector(early));links.retry(denied);runCurrent();val pending=links.control!!;links.retry(denied);links.retry(pending);runCurrent();assertEquals(3,repo.requests.size)
        repo.threads[1].complete(thread());runCurrent();repo.profiles[1].complete(JsonContracts.clientProfile(fixture("client-101-701")));runCurrent();val current=links.control
        links.retry(denied);assertFalse(links.closeInspector(deniedReturn));runCurrent();assertEquals(4,repo.requests.size);assertEquals(current,links.control);assertNotEquals(denied.profile,current!!.profile);assertEquals(701,links.profile.state.detail?.client?.id)
    }
    @Test fun lateThreadCompletionAndWithheldLinkCannotLoadCachedOrForeignClient()=runTest {
        val repo=Repo();repo.hold=true;val links=InboxClientModel(repo,backgroundScope);links.bind(thread(),first) {_,_->};links.openEntry(links.entryControl);runCurrent()
        links.bind(thread(202,951),second) {_,_->};val current=links.control;repo.threads[0].complete(thread());runCurrent();assertEquals(current,links.control);assertEquals(second,links.state.request);assertEquals(1,repo.requests.size);assertNull(links.profile.state.detail)
        val hidden=Repo();hidden.fresh=thread().copy(clientRefID=null);val h=InboxClientModel(hidden,backgroundScope);h.bind(thread(),first) {_,_->};h.openEntry(h.entryControl);runCurrent()
        assertNull(h.entryControl);assertNull(h.state.selectedID);assertNull(h.profile.state.detail);assertEquals(1,hidden.requests.size);h.openEntry(h.entryControl);runCurrent();assertEquals(1,hidden.requests.size)
    }
    @Test fun nestedWorkReturnAndRootReplySnapshotsPreserveDraftAndSourceThread()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Repo();val model=InboxViewModel(repo)
        try {
            model.load(101,110);runCurrent();model.search("response");model.unreadOnly(true);model.open(901);runCurrent();val links=model.clientLinks!!;val reply=model.reply;val context=ReplyDraftContext(101,901,110)
            model.openReply(context,model.control);reply.update("Private unsent reply",reply.inputControl);reply.close(expected=reply.returnControl);val messages=model.state.thread!!.messages;val unread=model.state.thread!!.conversation.unreadCount;val rootBefore=model.returnControl
            model.openClientEntry(links.entryControl,model.control);runCurrent();val control=links.control!!;val beforeWork=links.returnControl!!;val work=links.profile.work!!
            model.backToThreadList(rootBefore);assertEquals(901,model.state.selectedID);work.open(ClientWorkTarget.Task(1401),presentation=work.presentation);runCurrent();val nested=links.returnControl!!;val count=repo.requests.size
            model.retryClient(control,model.control);assertFalse(links.closeInspector(beforeWork));assertFalse(links.closeInspector(nested));model.backToThreadList(model.returnControl);runCurrent();assertEquals(count,repo.requests.size);assertEquals(901,model.state.selectedID)
            val returned=links.profile.workReturnControl;assertEquals(ClientWorkBack.CLOSED,links.profile.backWork(returned));assertFalse(links.closeInspector(beforeWork));assertTrue(links.closeInspector(links.returnControl))
            assertEquals(messages,model.state.thread!!.messages);assertEquals(unread,model.state.thread!!.conversation.unreadCount);assertEquals("response",model.state.query);assertTrue(model.state.unreadOnly);assertEquals("Private unsent reply",reply.state.text)
            val beforeReply=model.returnControl;model.openReply(context,model.control);model.backToThreadList(beforeReply);assertEquals(901,model.state.selectedID);assertNotNull(reply.control);assertEquals("Private unsent reply",reply.state.text)
            reply.close(expected=reply.returnControl);model.backToThreadList(model.returnControl);assertNull(model.state.selectedID);assertNull(links.state.request)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun cancelOrForeignParentReplyNeverPublishesIndependentClientData()=runTest {
        for(canceled in listOf(false,true)) {
            val repo=Repo();repo.hold=true;val links=InboxClientModel(repo,backgroundScope);var failures=0;links.bind(thread(),first) {_,problem->if(problem!=null)failures++};links.openEntry(links.entryControl);runCurrent()
            if(canceled)repo.threads[0].completeExceptionally(CancellationException("synthetic")) else repo.threads[0].complete(thread(202,951));runCurrent()
            assertNull(links.state.selectedID);assertNull(links.profile.state.detail);assertEquals(1,repo.requests.size);assertEquals(if(canceled)0 else 1,failures)
        }
    }
}
