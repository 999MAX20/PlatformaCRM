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
import java.time.Instant
import java.time.ZoneId

@OptIn(ExperimentalCoroutinesApi::class)
class TaskScheduleReadTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun detail(fields: JSONObject): TaskDetails {
        val o=JSONObject(fixture("task-101-1101"));val d=o.getJSONObject("details");d.remove("reminder_at");d.remove("snoozed_until")
        fields.keys().forEach {d.put(it,fields.get(it))};return JsonContracts.taskDetails(o.toString())
    }
    private fun kind(value: TaskScheduleValue)=when(value) {TaskScheduleValue.NotSet->"not_set";TaskScheduleValue.Unknown->"unknown";is TaskScheduleValue.At->"instant"}
    @Test fun sharedFieldsDistinguishExplicitNullMissingInvalidTypesAndValidInstants() {
        val rows=JSONObject(fixture("task-schedule-read")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val fields=row.getJSONObject("fields");val d=detail(fields)
            assertTrue(d.validFor(101,1101));assertEquals(row.getString("name"),row.getString("reminder"),kind(d.reminderAt));assertEquals(row.getString("snoozed"),kind(d.snoozedUntil))
            val reminder=d.reminderAt;if(reminder is TaskScheduleValue.At)assertEquals(fields.getString("reminder_at"),reminder.raw)
            assertEquals("open",d.task.status)
        }
    }
    @Test fun businessTimezoneFormatsSameOffsetInstantWithoutDeviceFallbackOrCountdown() {
        val utc="2026-10-29T23:30:00Z";val offset="2026-10-30T04:30:00+05:00"
        assertEquals(Instant.parse(utc),Instant.parse(offset));assertEquals(30,Instant.parse(utc).atZone(ZoneId.of("Asia/Almaty")).dayOfMonth)
        assertEquals(formatAppointmentDate(utc,"Asia/Almaty","ru"),formatAppointmentDate(offset,"Asia/Almaty","ru"))
        assertNull(formatAppointmentDate(utc,null,"ru"));assertNull(formatAppointmentDate(utc,"Unknown/Zone","ru"))
    }
    private class Controlled: TaskReadRepository {
        val pages=mutableListOf<CompletableDeferred<TaskPage>>();val details=mutableListOf<CompletableDeferred<TaskDetails>>()
        override suspend fun tasks(business: Int)=CompletableDeferred<TaskPage>().also {pages+=it}.await()
        override suspend fun taskDetails(business: Int,id: Int)=CompletableDeferred<TaskDetails>().also {details+=it}.await()
    }
    @Test fun pendingFreshNullUnknownFailuresBackAndLateOwnerHidePriorSchedule()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Controlled();val model=TaskListViewModel(source)
        try {
            model.load(101,1);runCurrent();source.pages[0].complete(JsonContracts.tasks(fixture("tasks-101")));runCurrent()
            val known=detail(JSONObject().put("reminder_at","2026-10-29T23:30:00Z").put("snoozed_until","2026-10-30T02:15:00Z"))
            model.open(1101);runCurrent();assertNull(model.state.detail);source.details[0].complete(known);runCurrent();assertEquals(known.reminderAt,model.state.detail!!.reminderAt)
            for((n,payload) in listOf(detail(JSONObject().put("reminder_at",JSONObject.NULL).put("snoozed_until",JSONObject.NULL)),detail(JSONObject())).withIndex()) {
                model.open(1101);runCurrent();assertNull(model.state.detail);source.details[n+1].complete(payload);runCurrent();assertEquals(payload.reminderAt,model.state.detail!!.reminderAt);assertEquals(payload.snoozedUntil,model.state.detail!!.snoozedUntil)
            }
            for((n,problem) in listOf(ReadProblem.DENIED,ReadProblem.UNAVAILABLE).withIndex()) {
                model.open(1101);runCurrent();source.details[n+3].completeExceptionally(ReadException(problem));runCurrent();assertNull(model.state.detail);assertEquals(problem,model.state.detailProblem)
            }
            model.open(1101);runCurrent();model.back();source.details[5].complete(known);runCurrent();assertNull(model.state.detail);assertNull(model.state.selectedID)
            model.open(1101);runCurrent();model.reconcileCommentOwner(202,2);source.details[6].complete(known);runCurrent();assertNull(model.state.detail);assertNull(model.state.business)
        } finally {model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun existingDetailRequestAloneSuppliesReadFieldsWithoutNewRoutesOrMutation()=runTest {
        val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {request->requests+=request;ReadResponse(200,fixture("task-101-1101"))})
        val d=repo.taskDetails(101,1101);val count=requests.size;kind(d.reminderAt);kind(d.snoozedUntil)
        assertEquals(count,requests.size);assertEquals(listOf(ReadRequest("/api/mobile/v1/tasks/1101/",mapOf("business" to "101"))),requests)
    }
}
