package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.TaskListViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskReadTest {
    private fun fixture(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private fun page(business: Int = 101) = JsonContracts.tasks(fixture("tasks-$business"))
    private fun detail() = JsonContracts.taskDetails(fixture("task-101-1101"))
    private class Controlled : TaskReadRepository {
        val pages = mutableListOf<CompletableDeferred<TaskPage>>()
        val details = mutableListOf<CompletableDeferred<TaskDetails>>()
        override suspend fun tasks(business: Int) = CompletableDeferred<TaskPage>().also { pages += it }.await()
        override suspend fun taskDetails(business: Int, id: Int) = CompletableDeferred<TaskDetails>().also { details += it }.await()
    }
    private fun check(block: suspend TestScope.(TaskListViewModel, Controlled) -> Unit) = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val source = Controlled(); val model = TaskListViewModel(source)
        try { model.load(101); runCurrent(); source.pages[0].complete(page()); runCurrent(); block(model, source) }
        finally { model.viewModelScope.cancel(); Dispatchers.resetMain() }
    }
    @Test fun existingRoutesReadNullableDeadlinesAndStringPriorities() = runTest {
        val requests = mutableListOf<ReadRequest>()
        val repo = APIReadRepository(ReadTransport { request -> requests += request; ReadResponse(200, fixture(if (request.path == "/api/mobile/v1/tasks/") "tasks-101" else "task-101-1101")) })
        val page = repo.tasks(101); val detail = repo.taskDetails(101, 1101)
        assertTrue(page.validFor(101)); assertTrue(detail.validFor(101, 1101))
        assertNull(page.items.first { it.id == 1102 }.dueAt); assertEquals("high", detail.task.priority)
        assertEquals(listOf(ReadRequest("/api/mobile/v1/tasks/", mapOf("business" to "101", "limit" to "50")), ReadRequest("/api/mobile/v1/tasks/1101/", mapOf("business" to "101"))), requests)
        try { repo.taskDetails(101, 0); fail("Invalid ID reached transport") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_CONTEXT, e.problem) }
        assertEquals(2, requests.size)
    }
    @Test fun scopeCommentWindowAndWireTypesAreChecked() {
        val detail = detail()
        assertEquals(listOf(11012, 11011), detail.comments.map { it.id })
        assertFalse(detail.copy(business = 202).validFor(101, 1101))
        assertFalse(detail.copy(task = detail.task.copy(id = 999)).validFor(101, 1101))
        assertFalse(detail.copy(comments = listOf(detail.comments[0], detail.comments[0])).validFor(101, 1101))
        assertFalse(detail.copy(maxComments = 0).validFor(101, 1101)); assertTrue(detail.copy(maxComments = 2).commentsCapped)
        assertFalse(page().copy(items = listOf(detail.task.copy(dueAt = "invalid"))).validFor(101))
        val bad = JSONObject(fixture("task-101-1101")); bad.getJSONObject("task").put("priority", 2)
        try { JsonContracts.taskDetails(bad.toString()); fail("Numeric priority was stringified") } catch (e: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, e.problem) }
    }
    @Test fun localFiltersDetailBackAndUnknownIdentity() = check { model, source ->
        model.search(" ALPHA "); model.filter("open")
        assertEquals(listOf(1101), model.state.visible.map { it.id })
        model.open(1101); runCurrent(); source.details[0].complete(detail()); runCurrent(); model.back()
        assertEquals(" ALPHA ", model.state.query); assertEquals("open", model.state.status)
        assertEquals(listOf(1101), model.state.visible.map { it.id }); assertNull(model.state.selectedID)
        model.open(999); runCurrent(); assertEquals(1, source.details.size); assertEquals(1, source.pages.size)
    }
    @Test fun filterTagSurvivesRetryAndEmptyDataset() = check { model, source ->
        model.filter("open"); model.load(101); runCurrent()
        source.pages[1].completeExceptionally(ReadException(ReadProblem.DENIED)); runCurrent()
        assertEquals("open", model.state.status); assertTrue("Retained filter must still have a valid picker tag", model.state.statuses.contains("open"))
        model.load(101); runCurrent(); source.pages[2].complete(TaskPage(101, emptyList(), 0)); runCurrent()
        assertTrue(model.state.statuses.contains("open")); assertTrue(model.state.showsEmpty)
        model.filter(null); assertNull(model.state.status)
    }
    @Test fun backReopenAndNewRedactionRejectOldDetails() = check { model, source ->
        model.open(1101); runCurrent(); model.back(); model.open(1101); runCurrent()
        source.details[0].complete(detail()); runCurrent(); assertNull(model.state.detail); assertTrue(model.state.detailLoading)
        val fresh = detail().copy(task = detail().task.copy(title = null, dueAt = null, status = "future_status", priority = "future_priority"), description = null)
        source.details[1].complete(fresh); runCurrent(); model.back()
        assertNull(model.state.items[0].title); assertNull(model.state.items[0].dueAt)
        assertEquals("future_status", model.state.items[0].status); assertTrue(model.state.statuses.contains("future_status"))
    }
    @Test fun businessSwitchRejectsOldListAndDetail() = check { model, source ->
        model.search("Alpha"); model.filter("open"); model.open(1101); runCurrent()
        model.load(101); runCurrent(); model.load(202); runCurrent()
        assertTrue(model.state.items.isEmpty()); assertNull(model.state.selectedID); assertEquals("", model.state.query); assertNull(model.state.status)
        source.pages[2].complete(page(202)); runCurrent(); source.pages[1].complete(page()); source.details[0].complete(detail()); runCurrent()
        assertEquals(listOf(1201), model.state.items.map { it.id }); assertNull(model.state.detail)
    }
    @Test fun failureRetryPartialAndCompleteEmptyRemainDistinct() = check { model, source ->
        model.search("Alpha"); model.filter("open"); model.open(1101); runCurrent()
        source.details[0].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE)); runCurrent()
        assertEquals(ReadProblem.UNAVAILABLE, model.state.detailProblem)
        model.open(1101); runCurrent(); source.details[1].complete(detail().copy(business = 202)); runCurrent()
        assertEquals(ReadProblem.INVALID_PAYLOAD, model.state.detailProblem)
        model.open(1101); runCurrent(); source.details[2].complete(detail()); runCurrent(); model.back()
        assertEquals("Alpha", model.state.query); assertEquals("open", model.state.status)
        model.load(101); runCurrent(); source.pages[1].complete(TaskPage(101, emptyList(), 5)); runCurrent()
        assertTrue(model.state.partial); assertFalse(model.state.showsEmpty)
        model.load(101); runCurrent(); source.pages[2].complete(TaskPage(101, emptyList(), 0)); runCurrent()
        assertTrue(model.state.showsEmpty)
    }
    @Test fun cancellationAndClearingDoNotStrandOrRestoreDetail() = check { model, source ->
        model.search("Alpha"); model.filter("open"); model.open(1101); runCurrent()
        source.details[0].completeExceptionally(CancellationException()); runCurrent()
        assertNull(model.state.selectedID); assertFalse(model.state.detailLoading); assertEquals("Alpha", model.state.query)
        model.load(101); runCurrent(); source.pages[1].completeExceptionally(CancellationException()); runCurrent()
        assertFalse(model.state.loading); assertFalse(model.state.showsEmpty); assertNull(model.state.problem)
        model.load(101); runCurrent(); model.load(null); source.pages[2].complete(page()); runCurrent()
        assertNull(model.state.business); assertTrue(model.state.items.isEmpty()); assertNull(model.state.status)
    }
    @Test fun sharedTypedTaskFreeTextAndEveryOtherComparatorStayExactAndScoped() {
        val catalog=JSONObject(fixture("task-read-text-identity-cases"));val cases=catalog.getJSONArray("cases")
        fun text(o:JSONObject,k:String):String?=if(!o.has(k)||o.isNull(k))null else o.getString(k)
        fun integer(o:JSONObject,k:String):Int?=if(!o.has(k)||o.isNull(k))null else o.getInt(k)
        fun work(raw:String):WorkTask {val o=JSONObject(raw);return WorkTask(o.getInt("id"),text(o,"title"),o.getString("status"),text(o,"priority"),text(o,"due_at"),integer(o,"client_id"),integer(o,"business"),text(o,"cancelled_at"),integer(o,"cancelled_by"),text(o,"cancel_reason"),text(o,"updated_at"),text(o,"description"),integer(o,"created_by"),text(o,"created_at"))}
        fun comment(raw:String):TaskComment {val c=JSONObject(raw);val wrapper=JSONObject(fixture("task-101-1101")).put("comments",org.json.JSONArray().put(c));val parsed=JsonContracts.taskDetails(wrapper.toString()).comments.single();return parsed.copy(task=integer(c,"task"),author=if(c.opt("author") is Number)c.getInt("author")else null,authorName=text(c,"author_name"),authorEmail=text(c,"author_email"))}
        for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val changed=row.getBoolean("changed");val field=row.getString("field");val before=text(row,"before");val after=text(row,"after")
            if(row.getString("kind")=="bounded"){val a=JsonContracts.taskDetails(row.getString("before_json"));val b=JsonContracts.taskDetails(row.getString("after_json"));assertTrue(a.validFor(101,1101));assertTrue(b.validFor(101,1101));assertEquals(changed,a!=b)
                val left:String?;val right:String?;when(field){"task.title"->{left=a.task.title;right=b.task.title;assertEquals(changed,a.task!=b.task);assertEquals(a.description,b.description);assertEquals(a.comments,b.comments)};"details.description"->{left=a.description;right=b.description;assertEquals(a.task,b.task);assertEquals(changed,a.description!=b.description);assertEquals(a.comments,b.comments)};else->{left=a.comments[0].text;right=b.comments[0].text;assertEquals(a.task,b.task);assertEquals(a.description,b.description);assertEquals(changed,a.comments!=b.comments)}}
                assertEquals(before,left);assertEquals(after,right);assertEquals(a.clientRead,b.clientRead);assertEquals(a.appointmentRead,b.appointmentRead);assertEquals(a.commentsCapped,b.commentsCapped);assertEquals(a.maxComments,b.maxComments);assertEquals(!changed,FixtureTaskCommentDraftSource.verified(b,a))
                val read=TaskCommentRead(TaskCommentContext(101,1101,4200),1);val ca=TaskClientEditSource(read,a.task,a.clientRead);val cb=TaskClientEditSource(read,b.task,b.clientRead);val aa=TaskAppointmentEditSource(read,a.task,a.appointmentRead);val ab=TaskAppointmentEditSource(read,b.task,b.appointmentRead);assertEquals(a.task!=b.task,ca!=cb);assertEquals(a.task!=b.task,aa!=ab);assertEquals(ca.valid,cb.valid);assertEquals(aa.valid,ab.valid)
            }else{val a=work(row.getString("before_json"));val b=work(row.getString("after_json"));assertEquals(changed,a!=b);assertEquals(a.valid(),b.valid());assertEquals(before,if(field=="action.description")a.description else a.cancelReason);assertEquals(after,if(field=="action.description")b.description else b.cancelReason)}
        }
        val metadata=catalog.getJSONArray("nontext_cases");for(i in 0 until metadata.length()){val row=metadata.getJSONObject(i);val a=row.getString("before_json");val b=row.getString("after_json");when(row.getString("kind")){"work"->assertNotEquals(row.getString("field"),work(a),work(b));"comment"->assertNotEquals(row.getString("field"),comment(a),comment(b));else->assertNotEquals(row.getString("field"),JsonContracts.taskDetails(a),JsonContracts.taskDetails(b))}}
    }
    @Test fun actualTypedReferenceSourceRejectsChangedFreeTextRetainsReadonlyDetailAndNeverGrantsSubmit()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {val all=JSONObject(fixture("task-read-text-identity-cases")).getJSONArray("cases");for(i in 0 until all.length()){val row=all.getJSONObject(i);if(row.getString("kind")!="bounded")continue;val reference=JsonContracts.taskDetails(row.getString("before_json"));val after=JsonContracts.taskDetails(row.getString("after_json"));val changed=row.getBoolean("changed");val source=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,reference)};val details=java.util.ArrayDeque(listOf(row.getString("before_json"),row.getString("after_json"),row.getString("before_json")));val reads=mutableListOf<ReadRequest>();val path="/api/mobile/v1/tasks/1101/";val transport=ReadTransport {r->reads+=r;ReadResponse(200,if(r.path==path)details.removeFirst()else fixture("tasks-101"))};val owner=TaskListViewModel(APIReadRepository(transport),source)
                try{owner.load(101,4300+i);runCurrent();owner.open(1101);runCurrent();val model=owner.comment!!;assertTrue(model.state.available);assertEquals(reference,owner.state.detail);assertNull(owner.state.detailProblem);owner.openComment(model.state.read!!);val input=model.inputControl!!;model.update("Operator own unsent text",input);owner.back();owner.open(1101);runCurrent();assertEquals(after,owner.state.detail);assertNull(owner.state.detailProblem);assertEquals(!changed,model.state.available)
                    val actual=when(row.getString("field")){"task.title"->owner.state.detail!!.task.title;"details.description"->owner.state.detail!!.description;else->owner.state.detail!!.comments[0].text};assertEquals(if(row.isNull("after"))null else row.getString("after"),actual);model.update("stale overwritten",input);owner.openComment(model.state.read!!);if(changed){assertNull(model.state.selection);assertNull(model.inputControl)}else assertEquals("Operator own unsent text",model.state.text)
                    owner.back();owner.open(1101);runCurrent();owner.openComment(model.state.read!!);assertTrue(model.state.available);assertEquals("Operator own unsent text",model.state.text);assertNotEquals(input,model.inputControl);val before=reads.toList();model.prepare(model.control);assertFalse(model.canSubmit);assertEquals(0,model.retainedAttemptCount);assertEquals(TaskCommentPhase.REVIEW,model.state.phase);assertEquals(before,reads);assertEquals(4,reads.size);assertTrue(reads.takeLast(3).all {it.path==path && it.query==mapOf("business" to "101")})
                }finally{owner.viewModelScope.cancel()}
            }}finally{Dispatchers.resetMain()}
    }
}
