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
class TaskPeopleReadTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(person: Any?,business: Int=101): TaskDetails {
        val o=JSONObject(fixture("task-101-1101"));val d=o.getJSONObject("details");for(key in listOf("assignee","created_by")) {d.remove(key);if(person!=null)d.put(key,person)};o.put("business",business);return JsonContracts.taskDetails(o.toString())
    }
    @Test fun sourceMiniobjectNullMissingIdentityTypesAndDisplayFallbackAreDistinct() {
        val rows=JSONObject(fixture("task-people-read")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val person=if(row.has("value"))row.get("value") else null;val d=detail(person)
            assertTrue(d.validFor(101,1101))
            for(value in listOf(d.assignee,d.createdBy)) {
                val kind=when(value){MobileUserRead.NotSet->"not_set";MobileUserRead.Unknown->"unknown";is MobileUserRead.Person->"person"}
                assertEquals(row.getString("name"),row.getString("expected"),kind)
                if(value is MobileUserRead.Person) {val source=row.getJSONObject("value");assertEquals(source.getInt("id"),value.user.id);assertEquals(source.getString("email"),value.user.email);assertEquals(source.getString("full_name"),value.user.fullName);assertEquals(if(row.isNull("display"))null else row.getString("display"),value.user.displayName)}
            }
            assertEquals("open",d.task.status);assertNull(d.task.business);assertNull(d.task.updatedAt)
        }
    }
    private class Controlled: TaskReadRepository {
        val pages=mutableListOf<CompletableDeferred<TaskPage>>();val details=mutableListOf<CompletableDeferred<TaskDetails>>()
        override suspend fun tasks(business: Int)=CompletableDeferred<TaskPage>().also {pages+=it}.await()
        override suspend fun taskDetails(business: Int,id: Int)=CompletableDeferred<TaskDetails>().also {details+=it}.await()
    }
    @Test fun pendingReplacementFailuresForeignScopeBackAndEpochHidePreviousPeople()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source)
        try {
            model.load(101,1);runCurrent();source.pages[0].complete(JsonContracts.tasks(fixture("tasks-101")));runCurrent()
            val user=JSONObject().put("id",9001).put("email","fixture@example.invalid").put("full_name","Synthetic employee");val known=detail(user)
            model.open(1101);runCurrent();assertNull(model.state.detail);source.details[0].complete(known);runCurrent();assertEquals(known.assignee,model.state.detail!!.assignee)
            for((n,payload) in listOf(detail(JSONObject.NULL),detail(null),detail(JSONObject().put("id",9002).put("email","other@example.invalid").put("full_name","Other employee"))).withIndex()) {
                model.open(1101);runCurrent();assertNull(model.state.detail);source.details[n+1].complete(payload);runCurrent();assertEquals(payload.assignee,model.state.detail!!.assignee);assertEquals(payload.createdBy,model.state.detail!!.createdBy)
            }
            for((n,problem) in listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).withIndex()) {model.open(1101);runCurrent();source.details[n+4].completeExceptionally(ReadException(problem));runCurrent();assertNull(model.state.detail);assertEquals(problem,model.state.detailProblem)}
            model.open(1101);runCurrent();source.details[6].complete(detail(user,202));runCurrent();assertNull(model.state.detail);assertEquals(ReadProblem.INVALID_PAYLOAD,model.state.detailProblem)
            model.open(1101);runCurrent();model.back();source.details[7].complete(known);runCurrent();assertNull(model.state.detail)
            model.open(1101);runCurrent();model.reconcileCommentOwner(202,2);source.details[8].complete(known);runCurrent();assertNull(model.state.detail);assertNull(model.state.business)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun readingPeopleUsesExistingDetailOnlyAndDoesNotGrantUpdateOrTeamLookup()=runTest {
        val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {request->requests+=request;ReadResponse(200,fixture("task-101-1101"))})
        val d=repo.taskDetails(101,1101);assertEquals(MobileUserRead.NotSet,d.assignee);assertEquals(MobileUserRead.NotSet,d.createdBy)
        assertEquals(listOf(ReadRequest("/api/mobile/v1/tasks/1101/",mapOf("business" to "101"))),requests)
    }
}
