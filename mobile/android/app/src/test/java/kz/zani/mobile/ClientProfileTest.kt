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
class ClientProfileTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun profile(business: Int = 101, id: Int = 701) = JsonContracts.clientProfile(fixture("client-$business-$id"))
    private class Controlled : ClientProfileRepository {
        val pending = mutableListOf<CompletableDeferred<ClientProfile>>()
        override suspend fun clientProfile(business: Int, id: Int) = CompletableDeferred<ClientProfile>().also { pending += it }.await()
    }
    private fun check(block: suspend TestScope.(ClientProfileViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val source = Controlled(); val model = ClientProfileViewModel(source)
        try { block(model, source) } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun sourceProfileRouteNotesAndExplicitRelatedIdentity() = runTest {
        val requests = mutableListOf<ReadRequest>(); val repo = APIReadRepository(ReadTransport { requests += it; ReadResponse(200, fixture("client-101-701")) })
        val detail = repo.clientProfile(101, 701)
        assertTrue(detail.validFor(101, 701)); assertEquals("Synthetic client profile note", detail.notes)
        assertEquals(701, detail.appointments[0].clientID); assertEquals(5101, detail.appointments[0].appointment.id)
        assertEquals(listOf(ReadRequest("/api/mobile/v1/clients/701/", mapOf("business" to "101"))), requests)
        try { repo.clientProfile(101, 0); fail("Invalid Client requested") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, e.problem) }
        assertEquals(1, requests.size)
    }
    @Test fun wrongParentAssociationDuplicatesAndWindowCannotEnterProfile() {
        val detail = profile(); assertFalse(detail.copy(business = 202).validFor(101, 701))
        assertFalse(detail.copy(client = detail.client.copy(id = 702)).validFor(101, 701))
        assertFalse(detail.copy(appointments = listOf(detail.appointments[0].copy(clientID = 702))).validFor(101, 701))
        assertFalse(detail.copy(appointments = detail.appointments + detail.appointments).validFor(101, 701))
        assertFalse(detail.copy(maxRelated = 0).validFor(101, 701)); assertTrue(detail.copy(maxRelated = 1).historyCapped)
        assertTrue(profile(101, 702).appointments.isEmpty())
    }
    @Test fun newerReadReplacesWithheldContactsAndOlderReadCannotRestore() = check { model, source ->
        var published: ClientContact? = null
        model.load(101, 701) { _, contact -> published = contact }; runCurrent()
        model.load(101, 701) { _, contact -> published = contact }; runCurrent()
        val withheld = profile().copy(client = profile().client.copy(title = null, phone = null, email = null), notes = null)
        source.pending[1].complete(withheld); runCurrent(); source.pending[0].complete(profile()); runCurrent()
        assertNull(model.state.detail!!.client.title); assertNull(model.state.detail!!.notes); assertNull(published!!.phone)
    }
    @Test fun deniedAndInvalidProfileNeverFallbackToListData() = check { model, source ->
        var accepted = 0
        model.load(101, 701) { _, _ -> accepted++ }; runCurrent(); source.pending[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals(ReadProblem.DENIED, model.state.problem); assertNull(model.state.detail); assertEquals(0, accepted)
        model.load(101, 701) { _, _ -> accepted++ }; runCurrent(); source.pending[1].complete(profile(202,801)); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.problem); assertNull(model.state.detail); assertEquals(0, accepted)
        model.load(101, 701) { _, _ -> accepted++ }; runCurrent(); source.pending[2].complete(profile()); runCurrent(); assertEquals(1, accepted)
    }
    @Test fun backBusinessSwitchAndCancellationInvalidatePending() = check { model, source ->
        var accepted = 0
        model.load(101, 701) { _, _ -> accepted++ }; runCurrent(); model.clear()
        source.pending[0].complete(profile()); runCurrent(); assertNull(model.state.detail); assertEquals(0, accepted)
        model.load(101, 701); runCurrent(); model.load(202,801); runCurrent()
        source.pending[2].complete(profile(202,801)); source.pending[1].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertEquals(801, model.state.detail!!.client.id); assertNull(model.state.problem)
        model.load(202,801); runCurrent(); source.pending[3].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(model.state.loading); assertNull(model.state.detail); assertNull(model.state.problem)
    }
    @Test fun directoryUpdateIsScopedAndKeepsSearchAndBackContext() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val model = ClientDirectoryViewModel(ClientRepository { JsonContracts.clients(fixture("clients-101")) })
        try {
            model.load(101); runCurrent(); model.search("Alpha"); model.open(701)
            model.refreshContact(202, profile().client.copy(title = null)); assertNotNull(model.state.selected!!.title)
            model.refreshContact(101, profile().client.copy(title = null, phone = null, email = null)); assertNull(model.state.selected!!.title)
            model.back(); assertEquals("Alpha", model.state.query); assertTrue(model.state.visible.isEmpty())
            model.refreshContact(101, profile().client); assertNull(model.state.items[0].title)
        } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
}
