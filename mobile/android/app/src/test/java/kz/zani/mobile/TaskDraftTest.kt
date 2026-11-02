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
class TaskDraftTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private val a=TaskDraftContext(101,6)
    @Test fun titleRulesMatchSourceTrimAndCodepoint255Boundaries() {
        val rows=JSONObject(fixture("task-draft-validation")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val raw=row.getString("title");val v=TaskDraftValues(title=raw)
            assertEquals(row.getBoolean("required"),v.issues.any {it.problem==TaskDraftProblem.REQUIRED})
            assertEquals(row.getBoolean("too_long"),v.issues.any {it.problem==TaskDraftProblem.TITLE_LENGTH});assertEquals(raw,v.title)
        }
    }
    @Test fun existingPriorityChoicesAndOptionalLongDescriptionHaveNoInventedLimit() {
        assertEquals("normal",TaskDraftValues().priority)
        for(priority in TaskDraftValues.priorities) assertTrue(TaskDraftValues(title="A",description="Synthetic note\n".repeat(4000),priority=priority).issues.isEmpty())
        assertTrue(TaskDraftValues(title="A",priority="invented").issues.any {it.problem==TaskDraftProblem.PRIORITY})
    }
    @Test fun validationPreviewBackAndStaleCallbacksRetainRawInput() {
        val s=TaskDraftSession();assertFalse(s.open(a));s.bind(a);s.open(a);val old=s.state.selection!!
        s.update(TaskDraftField.DESCRIPTION,"Unsent note",old);assertFalse(s.prepare(old));assertEquals("Unsent note",s.state.values.description)
        s.update(TaskDraftField.TITLE," Title ",old);assertTrue(s.prepare(old));s.update(TaskDraftField.TITLE,"late",old);assertEquals(" Title ",s.state.review!!.values.title)
        s.back(old);s.back(old);s.open(a);val current=s.state.selection!!;s.discard(old);s.update(TaskDraftField.TITLE,"old",old)
        assertEquals(current,s.state.selection);assertEquals(" Title ",s.state.values.title);s.bind(a);assertEquals(current,s.state.selection)
    }
    @Test fun businessEpochAndExplicitDiscardClearOnlyTheirOwnedDraft() {
        val s=TaskDraftSession();s.bind(a);s.open(a);s.update(TaskDraftField.TITLE,"Private",s.state.selection!!)
        s.bind(a.copy(epoch=7));assertEquals(TaskDraftValues(),s.state.values);s.open(a.copy(epoch=7));s.update(TaskDraftField.TITLE,"New",s.state.selection!!);s.discard(s.state.selection!!)
        assertEquals(TaskDraftValues(),s.state.values);s.bind(TaskDraftContext(202,8));assertNull(s.state.selection);s.bind(TaskDraftContext(0,0));assertNull(s.state.context)
    }
    @Test fun taskListOwnerDoesNotCreateRowsOrRequestsAndRetainsInputOnRecoverableError()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));var calls=0;var fail=false
        val repo=object: TaskReadRepository {
            override suspend fun tasks(business: Int): TaskPage {calls++;if(fail)throw ReadException(ReadProblem.UNAVAILABLE);return JsonContracts.tasks(fixture("tasks-$business"))}
            override suspend fun taskDetails(business: Int,id: Int): TaskDetails {calls++;return JsonContracts.taskDetails(fixture("task-$business-$id"))}
        }
        val m=TaskListViewModel(repo)
        try {
            m.load(101,6);runCurrent();m.search("review");m.filter("done");val rows=m.state.items;val before=calls
            m.draft.open(a);val token=m.draft.state.selection!!;m.draft.update(TaskDraftField.TITLE,"Unsent Task",token);m.draft.prepare(token)
            assertEquals(before,calls);assertEquals(rows,m.state.items);assertNull(m.state.selectedID);assertEquals(TaskDraftPhase.REVIEW,m.draft.state.phase)
            m.draft.back(token);fail=true;m.load(101,6);runCurrent();assertEquals(token,m.draft.state.selection);assertEquals("Unsent Task",m.draft.state.values.title)
            assertEquals("review",m.state.query);assertEquals("done",m.state.status)
            fail=false;m.load(202,7);assertEquals(TaskDraftValues(),m.draft.state.values);runCurrent();m.draft.update(TaskDraftField.TITLE,"old event",token);assertEquals("",m.draft.state.values.title)
        } finally {m.back();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
