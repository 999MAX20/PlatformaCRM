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
class InboxClientTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun thread() = JsonContracts.thread(fixture("inbox-101-901"))
    private fun profile() = JsonContracts.clientProfile(fixture("client-101-701"))
    private class Controlled(val fixture: (String)->String) : InboxClientRepository,ClientWorkRepository {
        val threads = mutableListOf<CompletableDeferred<InboxThread>>(); val profiles = mutableListOf<CompletableDeferred<ClientProfile>>()
        val requests = mutableListOf<Triple<String,Int,Int>>()
        override suspend fun inbox(business: Int) = JsonContracts.inbox(fixture("inbox-$business"))
        override suspend fun thread(business: Int,id: Int): InboxThread { requests += Triple("thread",business,id); return CompletableDeferred<InboxThread>().also { threads+=it }.await() }
        override suspend fun clientProfile(business: Int,id: Int): ClientProfile { requests += Triple("client",business,id); return CompletableDeferred<ClientProfile>().also { profiles+=it }.await() }
        override suspend fun taskDetails(business: Int,id: Int) = JsonContracts.taskDetails(fixture("task-$business-$id"))
        override suspend fun appointment(business: Int,id: Int) = JsonContracts.detail(fixture("appointment-$business-$id"))
    }
    private fun check(block: suspend TestScope.(InboxViewModel,InboxClientModel,Controlled)->Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val repo = Controlled(::fixture); val model = InboxViewModel(repo)
        try { model.load(101); runCurrent(); model.open(901); runCurrent(); repo.threads[0].complete(thread()); runCurrent(); block(model,model.clientLinks!!,repo) }
        finally { model.back(); model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun onlyExplicitPositiveClientReferenceCanExposeAction() {
        assertEquals(701,thread().clientReferenceID)
        for (id in listOf(null,0,-1)) assertNull(thread().copy(clientRefID=id).clientReferenceID)
        val j = JSONObject(fixture("inbox-101-901")); j.getJSONObject("details").put("client",JSONObject.NULL).put("lead",JSONObject().put("id",701))
        assertNull(JsonContracts.thread(j.toString()).clientReferenceID)
        j.getJSONObject("details").put("client",JSONObject().put("id","701"))
        try { JsonContracts.thread(j.toString()); fail() } catch (error: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD,error.problem) }
    }
    @Test fun actualThreadRevalidationIndependentProfileAndLayeredBackPreserveContext() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { r ->
            requests += r; val b = r.query["business"]; val id = r.path.trimEnd('/').substringAfterLast('/')
            val name = when {
                r.path.endsWith("/inbox/") -> "inbox-$b"
                r.path.contains("/inbox/") -> "inbox-$b-$id"
                r.path.contains("/clients/") -> "client-$b-$id"
                else -> "task-$b-$id"
            }; ReadResponse(200,fixture(name))
        }); val model = InboxViewModel(repo)
        try {
            for ((b,id,client,task) in listOf(listOf(101,901,701,1401),listOf(202,951,801,2401))) {
                model.load(b); runCurrent(); model.search("response"); model.unreadOnly(true); model.open(id); runCurrent()
                val links = model.clientLinks!!; val request = links.state.request!!; val messages = model.state.thread!!.messages.map { it.id }; val before = requests.size
                assertNull(links.profile.state.detail); assertNull(links.state.selectedID)
                links.open(request); runCurrent(); assertEquals(client,links.profile.state.detail!!.client.id)
                assertEquals(before+2,requests.size); assertEquals(listOf("/api/mobile/v1/inbox/$id/","/api/mobile/v1/clients/$client/"),requests.takeLast(2).map { it.path })
                links.profile.work!!.open(ClientWorkTarget.Task(task)); runCurrent(); assertNotNull(links.profile.work!!.state.detail)
                assertTrue(model.backClient()); assertNotNull(links.profile.state.detail); assertEquals(client,links.state.selectedID)
                assertTrue(model.backClient()); assertNull(links.profile.state.detail); assertNull(links.profile.work!!.state.parent)
                assertEquals(messages,model.state.thread!!.messages.map { it.id }); assertEquals("response",model.state.query); assertTrue(model.state.unreadOnly); assertEquals(id,model.state.selectedID)
                model.back(); assertNull(links.state.request)
            }
        } finally { model.back(); model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun missingOrChangedRevalidatedRelationNeverReadsOldProfile() = check { model,links,s ->
        val request = links.state.request!!
        links.bind(thread().copy(clientRefID=null),request) { _,_ -> }; links.open(); runCurrent(); assertEquals(1,s.requests.size)
        model.open(901); runCurrent(); s.threads[1].complete(thread()); runCurrent()
        links.open(); runCurrent(); s.threads[2].complete(thread().copy(clientRefID=null)); runCurrent()
        assertNull(links.state.selectedID); assertNull(links.profile.state.detail); assertTrue(s.profiles.isEmpty()); assertNull(model.state.thread!!.clientReferenceID)
        model.open(901); runCurrent(); s.threads[3].complete(thread()); runCurrent(); links.open(); runCurrent(); s.threads[4].complete(thread().copy(clientRefID=702)); runCurrent()
        assertNull(links.state.selectedID); assertTrue(s.profiles.isEmpty()); assertEquals(702,model.state.thread!!.clientReferenceID)
    }
    @Test fun profileDenialWrongIdentityBusinessAndWithheldContactsNeverFallback() = check { model,links,s ->
        val invalid = listOf(profile().copy(client=profile().client.copy(id=702)),profile().copy(business=202))
        links.open(); runCurrent(); s.threads[1].complete(thread()); runCurrent(); s.profiles[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals(ReadProblem.DENIED,links.profile.state.problem); assertNull(links.profile.state.detail); assertNotNull(model.state.thread)
        invalid.forEachIndexed { n,p -> links.open(); runCurrent(); s.threads[n+2].complete(thread()); runCurrent(); s.profiles[n+1].complete(p); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,links.profile.state.problem); assertNull(links.profile.state.detail) }
        links.open(); runCurrent(); s.threads[4].complete(thread()); runCurrent(); s.profiles[3].complete(profile().copy(client=profile().client.copy(phone=null,email=null))); runCurrent()
        assertNull(links.profile.state.detail!!.client.phone); assertNull(links.profile.state.detail!!.client.email); assertEquals(901,model.state.selectedID)
    }
    @Test fun backReopenRejectsOldThreadErrorsAndOldProfileContacts() = check { model,links,s ->
        links.open(); runCurrent(); links.back(); links.open(); runCurrent()
        s.threads[1].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent(); s.threads[2].complete(thread()); runCurrent(); s.profiles[0].complete(profile()); runCurrent()
        assertNull(model.state.threadProblem); assertNotNull(links.profile.state.detail)
        links.back(); links.open(); runCurrent(); s.threads[3].complete(thread()); runCurrent(); links.back()
        links.open(); runCurrent(); s.threads[4].complete(thread()); runCurrent(); s.profiles[2].complete(profile().copy(client=profile().client.copy(phone=null))); runCurrent()
        s.profiles[1].complete(profile()); runCurrent(); assertNull(links.profile.state.detail!!.client.phone); assertEquals(701,links.state.selectedID)
    }
    @Test fun parentRefreshStaleUiAndBusinessChangeInvalidateDependentReads() = check { model,links,s ->
        val stale = links.state.request!!
        links.open(stale); runCurrent(); s.threads[1].complete(thread()); runCurrent(); model.open(901); runCurrent(); s.threads[2].complete(thread()); runCurrent()
        s.profiles[0].complete(profile()); runCurrent(); assertNull(links.profile.state.detail); assertNotEquals(stale,links.state.request)
        val count = s.requests.size; links.open(stale); runCurrent(); assertEquals(count,s.requests.size); assertFalse(links.back(stale))
        links.open(); runCurrent(); s.threads[3].complete(thread()); runCurrent(); model.load(202); runCurrent(); s.profiles[1].complete(profile()); runCurrent()
        assertNull(links.profile.state.detail); assertNull(links.state.request); assertEquals(202,model.state.business)
    }
    @Test fun freshThreadFailureCannotUseCachedBodyAndOwnerCancellationClearsChild() = check { model,links,s ->
        links.open(); runCurrent(); s.threads[1].completeExceptionally(CancellationException()); runCurrent()
        assertNull(links.state.selectedID); assertNotNull(model.state.thread); assertNull(model.state.threadProblem)
        links.open(); runCurrent(); s.threads[2].complete(thread().copy(business=202)); runCurrent()
        assertNull(model.state.thread); assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.threadProblem); assertNull(links.profile.state.detail)
        model.open(901); runCurrent(); s.threads[3].complete(thread()); runCurrent(); links.open(); runCurrent(); s.threads[4].complete(thread()); runCurrent()
        model.viewModelScope.cancel(); runCurrent(); s.profiles[0].complete(profile()); runCurrent()
        assertNull(links.state.selectedID); assertNull(links.profile.state.detail); assertFalse(links.state.loading)
    }
}
