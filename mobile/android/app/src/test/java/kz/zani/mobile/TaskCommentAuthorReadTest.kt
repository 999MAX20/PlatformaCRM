package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.ui.TaskListViewModel
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class TaskCommentAuthorReadTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    @Test fun sourceAuthorMiniobjectAndNullMissingMalformedHaveSeparateReadStates() {
        val original=JsonContracts.taskDetails(fixture("task-101-1101"));val rows=JSONObject(fixture("task-comment-author-read")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val o=JSONObject(fixture("task-101-1101"));val c=o.getJSONArray("comments").getJSONObject(0);c.remove("author");if(row.has("value"))c.put("author",row.get("value"));val d=JsonContracts.taskDetails(o.toString());val author=d.comments[0].authorRead
            val kind=when(author){MobileUserRead.NotSet->"not_set";MobileUserRead.Unknown->"unknown";is MobileUserRead.Person->"person"}
            assertEquals(row.getString("name"),row.getString("expected"),kind);assertTrue(d.validFor(101,1101));assertEquals(original.comments.map {it.id},d.comments.map {it.id});assertEquals(original.comments.map {it.text},d.comments.map {it.text});assertEquals(original.comments.map {it.createdAt},d.comments.map {it.createdAt})
            if(author is MobileUserRead.Person) {assertEquals(if(row.isNull("display"))null else row.getString("display"),author.user.displayName);assertNull(d.comments[0].author)}
        }
    }
    @Test fun numericActionAuthorNeverConstructsPersonAndReadObjectNeverActsAsCommandActor() {
        val c=JSONObject(fixture("task-comment-submit")).getJSONArray("validation_cases").getJSONObject(0).getJSONObject("response")
        val action=JsonContracts.taskCommentAction(c.toString());assertEquals(9001,action.author);assertEquals(MobileUserRead.Unknown,action.authorRead)
        c.put("author",JSONObject().put("id",9001).put("email","fixture@example.invalid").put("full_name","Synthetic employee"))
        try {JsonContracts.taskCommentAction(c.toString());fail("Read person became action actor")} catch(e: ReadException) {assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
    }
    @Test fun exactSharedUserLabelsPreserveDisplayFallbackNestedSourceAndIdentityBoundaries() {
        val catalog=JSONObject(fixture("mobile-user-display-text-cases"));val cases=catalog.getJSONArray("cases")
        fun person(d:TaskDetails,context:String)=when(context){"created_by"->d.createdBy;"assignee"->d.assignee;else->d.comments[0].authorRead}
        fun user(raw:String):MobileUserItem {val obj=JSONObject(raw);return MobileUserItem(obj.getInt("id"),obj.getString("email"),obj.getString("full_name"))}
        for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val a=JsonContracts.taskDetails(row.getString("before_json"));val b=JsonContracts.taskDetails(row.getString("after_json"));val left=user(row.getString("before_user_json"));val right=user(row.getString("after_user_json"));val changed=row.getBoolean("changed");val context=row.getString("context")
            assertEquals(left.id,right.id);assertTrue(left.valid);assertTrue(right.valid);assertEquals(changed,left!=right);assertEquals(if(row.isNull("before_display"))null else row.getString("before_display"),left.displayName);assertEquals(if(row.isNull("after_display"))null else row.getString("after_display"),right.displayName);assertEquals(MobileUserRead.Person(left),person(a,context));assertEquals(MobileUserRead.Person(right),person(b,context));assertEquals(changed,person(a,context)!=person(b,context));assertEquals(changed,a!=b);assertEquals(a.task,b.task);assertEquals(a.clientRead,b.clientRead);assertEquals(a.appointmentRead,b.appointmentRead);assertEquals(a.maxComments,b.maxComments);assertEquals(!changed,FixtureTaskCommentDraftSource.verified(b,a));if(context=="comment_author"){assertNull(a.comments[0].author);assertNull(b.comments[0].author)}
        }
        val a=user(catalog.getJSONObject("id_control_before").toString());val b=user(catalog.getJSONObject("id_control_other").toString());val invalid=user(catalog.getJSONObject("id_control_invalid").toString());assertNotEquals(a,b);assertFalse(invalid.valid);assertTrue(a.valid);assertTrue(b.valid)
    }
    @Test fun actualUserDisplayReadKeepsRawLabelsSeparateFromSourceAdmissionAndSubmitAuthority()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {val cases=JSONObject(fixture("mobile-user-display-text-cases")).getJSONArray("cases");for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val reference=JsonContracts.taskDetails(row.getString("before_json"));val after=JsonContracts.taskDetails(row.getString("after_json"));val changed=row.getBoolean("changed");val source=object:TaskCommentDraftSource {override suspend fun matchesFixture(detail:TaskDetails)=FixtureTaskCommentDraftSource.verified(detail,reference)};val pending=java.util.ArrayDeque(listOf(row.getString("before_json"),row.getString("after_json")));val reads=mutableListOf<ReadRequest>();val path="/api/mobile/v1/tasks/1101/";val repo=APIReadRepository(ReadTransport {r->reads+=r;ReadResponse(200,if(r.path==path)pending.removeFirst()else fixture("tasks-101"))});val owner=TaskListViewModel(repo,source)
                try{owner.load(101,4700+i);runCurrent();owner.open(1101);runCurrent();val model=owner.comment!!;assertTrue(model.state.available);assertEquals(reference,owner.state.detail);owner.openComment(model.state.read!!);val input=model.inputControl!!;model.update("Own unsent text",input);owner.back();owner.open(1101);runCurrent();assertEquals(after,owner.state.detail);assertNull(owner.state.detailProblem);assertEquals(!changed,model.state.available);val person=when(row.getString("context")){"created_by"->owner.state.detail!!.createdBy;"assignee"->owner.state.detail!!.assignee;else->owner.state.detail!!.comments[0].authorRead} as MobileUserRead.Person;val expected=JSONObject(row.getString("after_user_json"));assertEquals(expected.getString("email"),person.user.email);assertEquals(expected.getString("full_name"),person.user.fullName);assertEquals(if(row.isNull("after_display"))null else row.getString("after_display"),person.user.displayName)
                    model.update("Stale overwrite",input);owner.openComment(model.state.read!!);if(changed){assertNull(model.state.selection);assertNull(model.inputControl)}else{assertEquals("Own unsent text",model.state.text);model.prepare(model.control)};assertFalse(model.canSubmit);assertEquals(0,model.retainedAttemptCount);assertEquals(3,reads.size);assertTrue(reads.takeLast(2).all {it.path==path && it.query==mapOf("business" to "101")})
                }finally{owner.viewModelScope.cancel()}
            }}finally{Dispatchers.resetMain()}
    }
}
