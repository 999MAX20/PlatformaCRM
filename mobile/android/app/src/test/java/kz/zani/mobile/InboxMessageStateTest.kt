package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.InboxViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class InboxMessageStateTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun cases()=JSONObject(fixture("message-source-states")).getJSONArray("cases")
    private fun thread(name:String):InboxThread {val all=cases();return (0 until all.length()).map {all.getJSONObject(it)}.first {it.getString("name")==name}.let {JsonContracts.thread(it.getJSONObject("response").toString())}}
    @Test fun exactExistingStatesAndUnknownPreserveMessageIdentityOrderTextAndActor() {
        val all=cases();assertEquals(14,all.length())
        for(n in 0 until all.length()) {val row=all.getJSONObject(n);val t=JsonContracts.thread(row.getJSONObject("response").toString());val m=t.messages[0]
            assertTrue(t.validFor(101,901));assertEquals(listOf(9011,9012),t.messages.map {it.id});assertEquals(InboxMessageState.valueOf(row.getString("expected").uppercase()),m.sourceState)
            assertEquals("Synthetic inquiry about available time",m.text);assertEquals("client",m.senderType);assertEquals(InboxMessageState.SENT,t.messages[1].sourceState)
        }
        assertEquals(InboxMessageState.UNKNOWN,InboxMessageState.from(null));assertEquals("messageStateSent",InboxMessageState.SENT.copyKey)
    }
    @Test fun sameReadRouteDoesNotInferStatusFromDateDirectionOrPreview()=runTest {
        val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {requests+=it;ReadResponse(200,cases().getJSONObject(13).getJSONObject("response").toString())})
        val t=repo.thread(101,901);assertEquals(InboxMessageState.UNKNOWN,t.messages[0].sourceState);assertEquals(ReadRequest("/api/mobile/v1/inbox/901/",mapOf("business" to "101","limit" to "30")),requests.single())
    }
    @Test fun pendingMissingFailedDeniedBackAndEpochUseOnlyFreshThreadWithoutResend()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val replies=mutableListOf<CompletableDeferred<InboxThread>>();var lists=0
        val m=InboxViewModel(object:InboxRepository {override suspend fun inbox(business:Int):InboxList {lists++;return JsonContracts.inbox(fixture("inbox-101"))};override suspend fun thread(business:Int,id:Int)=CompletableDeferred<InboxThread>().also {replies+=it}.await()})
        try {
            m.load(101,1);runCurrent();m.search("Alpha");m.unreadOnly(true);m.open(901);runCurrent();replies[0].complete(thread("sent"));runCurrent();assertEquals(InboxMessageState.SENT,m.state.thread!!.messages[0].sourceState)
            m.retryThread(m.threadSelection);runCurrent();assertNull(m.state.thread);assertTrue(m.state.threadLoading);replies[1].complete(thread("missing"));runCurrent();assertEquals(InboxMessageState.UNKNOWN,m.state.thread!!.messages[0].sourceState)
            m.retryThread(m.threadSelection);runCurrent();replies[2].complete(thread("failed"));runCurrent();assertEquals(InboxMessageState.FAILED,m.state.thread!!.messages[0].sourceState);assertEquals("Alpha",m.state.query);assertTrue(m.state.unreadOnly)
            m.retryThread(m.threadSelection);runCurrent();replies[3].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(m.state.thread);assertEquals(ReadProblem.DENIED,m.state.threadProblem)
            m.retryThread(m.threadSelection);runCurrent();m.back();replies[4].complete(thread("sent"));runCurrent();assertNull(m.state.thread);assertNull(m.state.selectedID)
            m.open(901);runCurrent();m.reconcileHandoffOwner(101,2);replies[5].complete(thread("failed"));runCurrent();assertNull(m.state.business);assertNull(m.state.thread);assertNull(m.reply.state.context);assertEquals(1,lists);assertEquals(6,replies.size)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
