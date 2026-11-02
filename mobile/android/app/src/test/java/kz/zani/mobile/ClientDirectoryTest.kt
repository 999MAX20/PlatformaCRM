package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancel
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.ClientDirectoryViewModel
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ClientDirectoryTest {
    private fun fixture(business: Int) = javaClass.classLoader!!.getResourceAsStream("fixtures/clients-$business.json")!!.bufferedReader().use { it.readText() }
    private class Controlled : ClientRepository {
        val pending = mutableListOf<CompletableDeferred<ClientList>>()
        override suspend fun clients(business: Int) = CompletableDeferred<ClientList>().also { pending += it }.await()
    }
    private fun check(block: suspend TestScope.(ClientDirectoryViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val repository = Controlled(); val model = ClientDirectoryViewModel(repository)
        try { block(model, repository) }
        finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun existingReadRouteAndNullableContactProjection() = runTest {
        var request: ReadRequest? = null
        val repository = APIReadRepository(ReadTransport { request = it; ReadResponse(200, fixture(101)) })
        val page = repository.clients(101)
        assertEquals(ReadRequest("/api/mobile/v1/clients/", mapOf("business" to "101", "limit" to "50")), request)
        assertEquals(listOf(701, 702), page.items.map { it.id }); assertNull(page.items[1].phone); assertNull(page.items[1].email)
        request = null
        try { repository.clients(0); fail("Invalid Business was requested") } catch (error: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, error.problem) }
        assertNull(request)
    }
    @Test fun localSearchCardBackAndUnknownId() = check { model, source ->
        model.load(101); runCurrent(); source.pending[0].complete(JsonContracts.clients(fixture(101))); runCurrent()
        for (query in listOf(" ALPHA ", "000000001", "ALPHA@EXAMPLE.INVALID")) {
            model.search(query); assertEquals(listOf(701), model.state.visible.map { it.id })
        }
        model.open(701); assertEquals(701, model.state.selected!!.id); model.back()
        assertNull(model.state.selected); assertEquals("ALPHA@EXAMPLE.INVALID", model.state.query)
        model.open(999); assertNull(model.state.selected)
        model.search("Beta"); model.open(702); assertNull(model.state.selected!!.phone)
        model.back(); model.search("notAvailable"); assertTrue(model.state.visible.isEmpty()); assertTrue(model.state.showsEmpty)
        assertEquals(1, source.pending.size) // Search/card/back are entirely local.
    }
    @Test fun businessSwitchClearsDataQueryCardAndLateSuccess() = check { model, source ->
        model.load(101); runCurrent(); source.pending[0].complete(JsonContracts.clients(fixture(101))); runCurrent()
        model.search("Alpha"); model.open(701); model.load(101); runCurrent()
        model.load(202); runCurrent()
        assertEquals("", model.state.query); assertTrue(model.state.items.isEmpty()); assertNull(model.state.selected)
        source.pending[2].complete(JsonContracts.clients(fixture(202))); runCurrent()
        source.pending[1].complete(JsonContracts.clients(fixture(101))); runCurrent()
        assertEquals(202, model.state.business); assertEquals(listOf(801), model.state.items.map { it.id })
    }
    @Test fun newerRetryKeepsRedactionAndIgnoresOldFailure() = check { model, source ->
        val page = JsonContracts.clients(fixture(101))
        model.load(101); runCurrent(); model.search("Alpha"); model.load(101); runCurrent()
        source.pending[1].complete(page.copy(items = page.items.map { it.copy(title = null, phone = null, email = null) })); runCurrent()
        source.pending[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertNull(model.state.problem); assertFalse(model.state.loading); assertEquals("Alpha", model.state.query)
        assertTrue(model.state.visible.isEmpty()); assertTrue(model.state.items.all { it.title == null && it.phone == null && it.email == null })
    }
    @Test fun errorAndInvalidPayloadRetryPreserveScopedSearch() = check { model, source ->
        model.load(101); runCurrent(); model.search("Alpha")
        for ((index, problem) in listOf(ReadProblem.UNAVAILABLE, ReadProblem.DENIED).withIndex()) {
            source.pending[index].completeExceptionally(ReadException(problem)); runCurrent()
            assertEquals(problem, model.state.problem); assertEquals("Alpha", model.state.query); assertFalse(model.state.showsEmpty)
            model.load(101); runCurrent()
        }
        source.pending[2].complete(JsonContracts.clients(fixture(202))); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.problem); assertTrue(model.state.items.isEmpty())
        model.load(101); runCurrent(); source.pending[3].complete(JsonContracts.clients(fixture(101))); runCurrent()
        assertNull(model.state.problem); assertEquals(listOf(701), model.state.visible.map { it.id })
    }
    @Test fun partialZeroIsNotCompleteEmptyAndNilScopeInvalidatesPending() = check { model, source ->
        assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pending[0].complete(ClientList(101, emptyList(), 5)); runCurrent()
        assertTrue(model.state.partial); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pending[1].complete(ClientList(101, emptyList(), 0)); runCurrent()
        assertTrue(model.state.showsEmpty)
        model.load(101); runCurrent(); model.load(null)
        source.pending[2].complete(JsonContracts.clients(fixture(101))); runCurrent()
        assertNull(model.state.business); assertTrue(model.state.items.isEmpty()); assertFalse(model.state.showsEmpty)
    }
}
