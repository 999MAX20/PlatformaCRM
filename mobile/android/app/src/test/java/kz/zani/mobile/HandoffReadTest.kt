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
class HandoffReadTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun variant(flag: Any?,present: Boolean=true): InboxThread {
        val json=JSONObject(fixture("inbox-101-901"));val conversation=json.getJSONObject("conversation")
        if(present)conversation.put("handoff_required",flag ?: JSONObject.NULL) else conversation.remove("handoff_required")
        json.getJSONObject("details").put("bot_enabled",false).put("handoff_reason","Synthetic safety marker")
        return JsonContracts.thread(json.toString())
    }
    @Test fun strictTrueFalseAndUnknownNeverUseTruthinessAiReasonOrOutboundMessage() {
        val cases=JSONObject(fixture("inbox-handoff-read-cases")).getJSONArray("cases")
        for(n in 0 until cases.length()) {
            val row=cases.getJSONObject(n);val thread=variant(row.opt("value"),row.getBoolean("present"));assertTrue(thread.validFor(101,901))
            val expected=when(row.getString("expected")){"required"->HandoffReadState.REQUIRED;"notRequired"->HandoffReadState.NOT_REQUIRED;else->HandoffReadState.UNKNOWN}
            assertEquals(expected,thread.conversation.handoffState);assertEquals(2,thread.conversation.unreadCount)
        }
        assertEquals(3,HandoffReadState.entries.map {it.copyKey}.toSet().size)
    }
    private class Controlled(val pages: Map<Int,InboxList>): InboxRepository {
        val threads=mutableListOf<CompletableDeferred<InboxThread>>()
        override suspend fun inbox(business: Int)=pages.getValue(business)
        override suspend fun thread(business: Int,id: Int)=CompletableDeferred<InboxThread>().also {threads+=it}.await()
    }
    private fun controlled()=Controlled(mapOf(101 to JsonContracts.inbox(fixture("inbox-101")),202 to JsonContracts.inbox(fixture("inbox-202"))))
    @Test fun independentDetailReplacesCachedFalseTrueAndMissingWithoutFallback()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=controlled();val model=InboxViewModel(source)
        try {
            model.load(101,10);runCurrent();assertNull(model.handoffState)
            model.open(901);runCurrent();assertNull(model.handoffState);source.threads[0].complete(variant(true));runCurrent();assertEquals(HandoffReadState.REQUIRED,model.handoffState)
            model.open(901);assertNull(model.handoffState);runCurrent();source.threads[1].complete(variant(null,false));runCurrent()
            assertEquals(HandoffReadState.UNKNOWN,model.handoffState);assertNull(model.state.items[0].handoffRequired)
            model.open(901);runCurrent();model.open(901);runCurrent();source.threads[3].complete(variant(false));runCurrent();source.threads[2].complete(variant(true));runCurrent();assertEquals(HandoffReadState.NOT_REQUIRED,model.handoffState)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun staleUiCallbacksBackRetryAndSameBusinessEpochCannotRestorePriorFlag()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=controlled();val model=InboxViewModel(source)
        try {
            model.load(101,20);runCurrent();model.open(901);runCurrent();source.threads[0].complete(variant(true));runCurrent();val old=model.threadSelection!!
            model.open(901);runCurrent();source.threads[1].complete(variant(false));runCurrent();val current=model.threadSelection!!
            model.back(old);model.retryThread(old);runCurrent();assertEquals(current,model.threadSelection);assertEquals(2,source.threads.size);assertEquals(HandoffReadState.NOT_REQUIRED,model.handoffState)
            model.open(901);runCurrent();model.load(101,21);runCurrent();source.threads[2].complete(variant(true));runCurrent();assertNull(model.handoffState);assertNull(model.state.thread)
            model.open(901);runCurrent();model.load(202,22);runCurrent();model.open(951);runCurrent();source.threads[4].complete(JsonContracts.thread(fixture("inbox-202-951")));runCurrent();source.threads[3].complete(variant(true));runCurrent()
            assertEquals(202,model.state.business);assertEquals(HandoffReadState.NOT_REQUIRED,model.handoffState)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun deniedUnavailableBackAndOffTabOwnerHideInsteadOfShowingFalseOrCachedTrue()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=controlled();val model=InboxViewModel(source)
        try {
            model.load(101,30);runCurrent()
            listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).forEachIndexed {n,problem->model.open(901);runCurrent();source.threads[n].completeExceptionally(ReadException(problem));runCurrent();assertEquals(problem,model.state.threadProblem);assertNull(model.handoffState)}
            model.open(901);runCurrent();model.back();source.threads[2].complete(variant(true));runCurrent();assertNull(model.handoffState)
            model.open(901);runCurrent();model.reconcileHandoffOwner(202,31);source.threads[3].complete(variant(true));runCurrent();assertNull(model.threadSelection);assertNull(model.handoffState)
            val count=source.threads.size;model.open(901);runCurrent();assertNull(model.state.business);assertTrue(model.state.items.isEmpty());assertEquals(count,source.threads.size)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun readBadgeAndUnsentReplyPreviewHaveNoRequestsUnreadMessageAiOrTimerEffects()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->requests+=r;ReadResponse(200,fixture(if(r.path.endsWith("inbox/"))"inbox-101" else "inbox-101-901"))});val model=InboxViewModel(repo);val unscoped=InboxViewModel(repo)
        try {
            unscoped.load(101);runCurrent();unscoped.open(901);runCurrent();assertNull(unscoped.handoffState)
            model.load(101,40);runCurrent();model.open(901);runCurrent();val count=requests.size;val detail=model.state.thread;val handoff=model.handoffState
            val context=ReplyDraftContext(101,901,40);model.reply.open(context);val selection=model.reply.state.selection!!;model.reply.update("Manual unsent reply",selection);model.reply.prepare(selection)
            assertEquals(count,requests.size);assertEquals(detail,model.state.thread);assertEquals(handoff,model.handoffState);assertEquals(2,model.state.thread!!.conversation.unreadCount)
        } finally {model.viewModelScope.cancel();unscoped.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
