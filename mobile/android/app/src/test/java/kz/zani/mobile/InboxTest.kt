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
class InboxTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun page(business: Int = 101) = JsonContracts.inbox(fixture("inbox-$business"))
    private fun thread() = JsonContracts.thread(fixture("inbox-101-901"))
    private class Controlled : InboxRepository {
        val pages = mutableListOf<CompletableDeferred<InboxList>>()
        val threads = mutableListOf<CompletableDeferred<InboxThread>>()
        override suspend fun inbox(business: Int) = CompletableDeferred<InboxList>().also { pages += it }.await()
        override suspend fun thread(business: Int, id: Int) = CompletableDeferred<InboxThread>().also { threads += it }.await()
    }
    private fun check(block: suspend TestScope.(InboxViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val source = Controlled(); val model = InboxViewModel(source)
        try {
            model.load(101); runCurrent(); source.pages[0].complete(page()); runCurrent()
            block(model, source)
        } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun existingReadRoutesTypesAndInvalidContext() = runTest {
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { request ->
            requests += request
            ReadResponse(200, fixture(if (request.path == "/api/mobile/v1/inbox/") "inbox-101" else "inbox-101-901"))
        })
        assertTrue(repo.inbox(101).validFor(101)); assertTrue(repo.thread(101, 901).validFor(101, 901))
        assertEquals(listOf(ReadRequest("/api/mobile/v1/inbox/", mapOf("business" to "101", "limit" to "50")), ReadRequest("/api/mobile/v1/inbox/901/", mapOf("business" to "101", "limit" to "30"))), requests)
        try { repo.thread(101, 0); fail("Invalid identity reached transport") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, e.problem) }
        assertEquals(2, requests.size)
        val bad = JSONObject(fixture("inbox-101-901")); bad.getJSONArray("messages").getJSONObject(0).put("conversation_id", "901")
        try { JsonContracts.thread(bad.toString()); fail("String message identity coerced") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, e.problem) }
    }
    @Test fun messageScopeIdentityAndWindowAreValidated() {
        val detail = thread()
        assertEquals(listOf(9011, 9012), detail.messages.map { it.id }); assertFalse(detail.windowCapped)
        assertFalse(detail.copy(business = 202).validFor(101, 901))
        assertFalse(detail.copy(messages = listOf(detail.messages[0].copy(conversationID = 999))).validFor(101, 901))
        assertFalse(detail.copy(messages = listOf(detail.messages[0], detail.messages[0])).validFor(101, 901))
        assertFalse(detail.copy(maxMessages = 0).validFor(101, 901))
        assertTrue(detail.copy(maxMessages = 2).windowCapped)
        assertFalse(page().copy(items = listOf(page().items[0].copy(unreadCount = -1))).validFor(101))
    }
    @Test fun searchUnreadThreadAndBackAreLocalAndDoNotMarkRead() = check { model, source ->
        model.search(" ALPHA "); model.unreadOnly(true)
        assertEquals(listOf(901), model.state.visible.map { it.id })
        model.search("operator response"); assertEquals(listOf(901), model.state.visible.map { it.id })
        model.search("Alpha"); model.open(901); runCurrent(); source.threads[0].complete(thread()); runCurrent()
        assertEquals(2, model.state.thread!!.conversation.unreadCount)
        model.back(); assertEquals("Alpha", model.state.query); assertTrue(model.state.unreadOnly)
        assertEquals(listOf(901), model.state.visible.map { it.id }); assertNull(model.state.thread)
        model.open(999); runCurrent(); assertNull(model.state.selectedID)
        assertEquals(1, source.pages.size); assertEquals(1, source.threads.size)
    }
    @Test fun backReopenAndOlderSuccessCannotRestoreRedactedThread() = check { model, source ->
        model.open(901); runCurrent(); model.back(); model.open(901); runCurrent()
        source.threads[0].complete(thread()); runCurrent()
        assertNull(model.state.thread); assertTrue(model.state.threadLoading)
        val fresh = thread().copy(conversation = thread().conversation.copy(title = null, channel = null), messages = thread().messages.map { it.copy(text = null) })
        source.threads[1].complete(fresh); runCurrent(); model.back()
        assertNull(model.state.items[0].title); assertNull(model.state.items[0].preview)
    }
    @Test fun businessSwitchRejectsLateListAndThreadResults() = check { model, source ->
        model.search("Alpha"); model.unreadOnly(true); model.open(901); runCurrent()
        model.load(101); runCurrent(); model.load(202); runCurrent()
        assertTrue(model.state.items.isEmpty()); assertNull(model.state.selectedID); assertEquals("", model.state.query); assertFalse(model.state.unreadOnly)
        source.pages[2].complete(page(202)); runCurrent()
        source.pages[1].complete(page()); source.threads[0].complete(thread()); runCurrent()
        assertEquals(listOf(951), model.state.items.map { it.id }); assertNull(model.state.thread)
    }
    @Test fun listFailureRetryPartialAndCompleteEmptyStayDistinct() = check { model, source ->
        model.search("Alpha"); model.unreadOnly(true); model.load(101); runCurrent()
        source.pages[1].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertFalse(model.state.showsEmpty); assertEquals("Alpha", model.state.query); assertTrue(model.state.unreadOnly)
        model.load(101); runCurrent(); source.pages[2].complete(InboxList(101, emptyList(), 5)); runCurrent()
        assertTrue(model.state.partial); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[3].complete(InboxList(101, emptyList(), 0)); runCurrent()
        assertTrue(model.state.showsEmpty); assertNull(model.state.problem)
    }
    @Test fun threadErrorsRetryAndForeignMessagesPreserveListContext() = check { model, source ->
        model.search("Alpha"); model.open(901); runCurrent()
        source.threads[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertEquals(ReadProblem.UNAVAILABLE, model.state.threadProblem)
        model.open(901); runCurrent(); source.threads[1].complete(thread().copy(messages = listOf(thread().messages[0].copy(conversationID = 902)))); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.threadProblem); assertNull(model.state.thread)
        model.open(901); runCurrent(); source.threads[2].complete(thread()); runCurrent(); model.back()
        assertEquals("Alpha", model.state.query); assertEquals(listOf(901, 902), model.state.items.map { it.id }); assertEquals(1, source.pages.size)
    }
    @Test fun clearScopeInvalidatesPendingReadsAndErrors() = check { model, source ->
        model.open(901); runCurrent(); model.load(null)
        source.threads[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertNull(model.state.business); assertNull(model.state.threadProblem); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); model.load(null); source.pages[1].complete(page()); runCurrent()
        assertTrue(model.state.items.isEmpty()); assertFalse(model.state.loading)
    }
    @Test fun cancelledReadsKeepARecoverableListInsteadOfBlankThread() = check { model, source ->
        model.search("Alpha"); model.unreadOnly(true); model.open(901); runCurrent()
        source.threads[0].completeExceptionally(CancellationException()); runCurrent()
        assertNull(model.state.selectedID); assertFalse(model.state.threadLoading)
        assertEquals("Alpha", model.state.query); assertTrue(model.state.unreadOnly)
        model.load(101); runCurrent(); source.pages[1].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(model.state.loading); assertFalse(model.state.showsEmpty); assertNull(model.state.problem)
        model.load(101); runCurrent(); source.pages[2].complete(page()); runCurrent()
        assertEquals(listOf(901), model.state.visible.map { it.id })
    }
}
