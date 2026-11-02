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
class AttentionQueueTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun page(b: Int = 101) = JsonContracts.actions(fixture("actions-$b"))
    private fun task(b: Int = 101) = JsonContracts.taskDetails(fixture(if (b == 101) "task-101-1111" else "task-202-1211"))
    private fun thread() = JsonContracts.thread(fixture("inbox-101-911"))
    private fun appointment() = JsonContracts.detail(fixture("appointment-101-511"))
    private class Controlled : AttentionRepository {
        val pages = mutableListOf<CompletableDeferred<AttentionPage>>()
        val details = mutableListOf<CompletableDeferred<AttentionDetail>>()
        val targets = mutableListOf<Triple<Int, AttentionKind, Int>>()
        override suspend fun actions(business: Int) = CompletableDeferred<AttentionPage>().also { pages += it }.await()
        private suspend fun target(b: Int, kind: AttentionKind, id: Int): AttentionDetail { targets += Triple(b,kind,id); return CompletableDeferred<AttentionDetail>().also { details += it }.await() }
        override suspend fun taskDetails(business: Int, id: Int) = (target(business,AttentionKind.TASK,id) as AttentionDetail.TaskRead).value
        override suspend fun thread(business: Int, id: Int) = (target(business,AttentionKind.CONVERSATION,id) as AttentionDetail.ThreadRead).value
        override suspend fun appointment(business: Int, id: Int) = (target(business,AttentionKind.APPOINTMENT,id) as AttentionDetail.AppointmentRead).value
    }
    private fun check(block: suspend TestScope.(AttentionQueueViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val source = Controlled(); val model = AttentionQueueViewModel(source)
        try { block(model,source) } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun exactReadRouteAndInvalidScopeDoesNotContactTransport() = runTest {
        val requests = mutableListOf<ReadRequest>(); val repo = APIReadRepository(ReadTransport { requests += it; ReadResponse(200,fixture("actions-101")) })
        assertTrue(repo.actions(101).validFor(101)); assertEquals(listOf(ReadRequest("/api/mobile/v1/actions/",mapOf("business" to "101","limit" to "20"))),requests)
        try { repo.actions(0); fail() } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT,e.problem) }
        assertEquals(1,requests.size)
    }
    @Test fun onlyExactTypedSourceIdentityAndHrefCanOfferReadTarget() {
        val p = page(); assertEquals(listOf(null,AttentionKind.TASK,AttentionKind.CONVERSATION,null,AttentionKind.APPOINTMENT),p.items.map { it.readTarget?.kind })
        val a = p.items.last()
        listOf(null,"https://example.invalid/app/calendar?appointment=511","//app/calendar?appointment=511","/app/calendar?appointment=512","/app/calendar?appointment=511&x=1","/app/calendar?appointment=511#x","/app/calendar?appointment=%35%31%31","/app/leads?lead=511").forEach { href -> assertNull(a.copy(entity=a.entity.copy(href=href)).readTarget) }
        assertNull(a.copy(type="lead").readTarget); assertNull(a.copy(type="deal").readTarget); assertNull(a.copy(key="future_key").readTarget)
        assertNull(p.items[0].copy(entity=p.items[0].entity.copy(href="/app/tasks?task=1111")).readTarget)
    }
    @Test fun windowTotalIsReturnedCountNotGlobalCompletenessAndOrderIsPreserved() {
        val p = page(); assertTrue(p.validFor(101)); assertFalse(p.windowCapped)
        assertTrue(p.copy(limit=5,maxItems=5).windowCapped); assertFalse(p.copy(total=99).validFor(101))
        assertFalse(p.copy(maxItems=0).validFor(101)); assertFalse(p.copy(limit=4,maxItems=4).validFor(101))
        val empty=p.copy(items=emptyList(),total=0); assertTrue(empty.validFor(101)); assertFalse(empty.windowCapped)
        val reverse=p.copy(items=p.items.reversed()); assertEquals(listOf(30,20,15,10,5),reverse.items.map { it.priority }); assertTrue(reverse.validFor(101))
    }
    @Test fun compositeIdentityRejectsDuplicateButNotSameNumericIdOfOtherType() {
        val p=page(); assertEquals(1111,p.items[0].entity.id); assertEquals(1111,p.items[1].entity.id); assertNotEquals(p.items[0].identity,p.items[1].identity)
        assertEquals(p.items.size,p.items.map { it.stableKey }.distinct().size)
        assertFalse(p.copy(items=p.items+p.items[0],total=6).validFor(101)); assertFalse(p.copy(business=202).validFor(101))
    }
    @Test fun parserAcceptsWithheldTitleAndUnknownFieldsButRejectsWrongNumberTypes() {
        val j=JSONObject(fixture("actions-101")); j.put("future",true); val entity=j.getJSONArray("items").getJSONObject(1).getJSONObject("entity"); entity.put("title",JSONObject.NULL)
        assertNull(JsonContracts.actions(j.toString()).items[1].entity.title)
        entity.put("id","1111"); try { JsonContracts.actions(j.toString()); fail() } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem) }
    }
    @Test fun unsupportedRowsDoNotRequestAnythingAndDenialHasNoCachedDetail() = check { model,source ->
        model.load(101); runCurrent(); source.pages[0].complete(page()); runCurrent()
        listOf(0,3).forEach { model.open(model.state.items[it].identity) }; runCurrent(); assertTrue(source.targets.isEmpty()); assertNull(model.state.selectedID)
        model.open(model.state.items[1].identity); runCurrent(); source.details[0].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals(ReadProblem.DENIED,model.state.detailProblem); assertNull(model.state.detail)
        model.open(model.state.selectedID!!); runCurrent(); source.details[1].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertNotNull(model.state.detail)
    }
    @Test fun threeRealReadTargetsBackAndSearchRetainServerWindow() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler)); val requests=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport { request ->
            requests+=request; val b=request.query["business"]; val id=request.path.trimEnd('/').substringAfterLast('/')
            val name=when { request.path.endsWith("/actions/") -> "actions-$b"; request.path.contains("/tasks/") -> "task-$b-$id"; request.path.contains("/inbox/") -> "inbox-$b-$id"; else -> "appointment-$b-$id" }
            ReadResponse(200,fixture(name))
        }); val model=AttentionQueueViewModel(repo)
        try {
            model.load(101); runCurrent(); val identities=model.state.items.map { it.identity }; model.search("attention")
            for (row in model.state.visible.toList()) { model.open(row.identity); runCurrent(); assertNotNull(model.state.detail); model.back(); assertEquals("attention",model.state.query); assertEquals(identities,model.state.items.map { it.identity }) }
            assertEquals(listOf("/api/mobile/v1/actions/","/api/mobile/v1/tasks/1111/","/api/mobile/v1/inbox/911/","/api/mobile/v1/appointments/511/"),requests.map { it.path })
            assertEquals(3,model.state.visible.size)
        } finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun retryBackAndRedactionRejectLateSameTargetSuccessAndError() = check { model,source ->
        model.load(101); runCurrent(); source.pages[0].complete(page()); runCurrent(); val id=model.state.items[1].identity
        model.open(id); runCurrent(); model.open(id); runCurrent()
        source.details[1].complete(AttentionDetail.TaskRead(task().copy(task=task().task.copy(title=null)))); runCurrent()
        source.details[0].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertNull(model.state.items[1].entity.title); assertNull(model.state.detail!!.title)
        model.open(id); runCurrent(); model.back(); model.open(id); runCurrent()
        source.details[2].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); source.details[3].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertNull(model.state.detailProblem)
        model.open(id); runCurrent(); model.back(); source.details[4].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertNull(model.state.detail); assertNull(model.state.selectedID)
    }
    @Test fun businessAndQueueRetryInvalidateBothListAndDetailResponses() = check { model,source ->
        model.load(101); runCurrent(); model.load(101); runCurrent(); source.pages[1].complete(page()); source.pages[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent(); assertNull(model.state.problem)
        model.search("attention"); model.open(model.state.items[1].identity); runCurrent(); model.load(202); runCurrent()
        assertTrue(model.state.query.isEmpty()); assertNull(model.state.selectedID)
        source.pages[2].complete(page(202)); source.details[0].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertEquals(202,model.state.business); assertNull(model.state.detail)
        model.open(model.state.items[0].identity); runCurrent(); source.details[1].complete(AttentionDetail.TaskRead(task())); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.detailProblem)
    }
    @Test fun cancellationAndInvalidPayloadDoNotBecomeEmptyOrLeaveLoading() = check { model,source ->
        model.load(101); runCurrent(); source.pages[0].completeExceptionally(CancellationException()); runCurrent(); assertFalse(model.state.loading); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[1].complete(page().copy(total=88)); runCurrent(); assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.problem); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[2].complete(page()); runCurrent(); model.open(model.state.items[1].identity); runCurrent(); source.details[0].completeExceptionally(CancellationException()); runCurrent()
        assertNull(model.state.selectedID); assertFalse(model.state.detailLoading); assertTrue(model.state.loaded)
        model.load(null); assertFalse(model.state.showsEmpty); assertTrue(model.state.items.isEmpty())
    }
}
