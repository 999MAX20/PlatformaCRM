package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.data.NotificationRepository
import kz.zani.mobile.ui.NotificationCenterViewModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class NotificationRouteTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page()=JsonContracts.notifications(fixture("notifications-101"))
    private class Repo(val page:NotificationPage):NotificationRepository {
        var lists=0;var targets=0
        override suspend fun notifications(business:Int):NotificationPage {++lists;return page}
        override suspend fun appointment(business:Int,id:Int):AppointmentDetail {++targets;error("Route must not fetch")}
    }
    private fun ready(repo:Repo):NotificationCenterViewModel=NotificationCenterViewModel(repo).also {it.load(101,1)}
    @Test fun exactSharedSyntaxIncludesOverflowAndNoNormalization() {
        val cases=JSONObject(fixture("relative-appointment-candidate")).getJSONArray("parse_cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val raw=row.getString("raw");val candidate=RelativeAppointmentCandidate.parse(raw)
            assertEquals(row.getString("name"),if(row.isNull("candidate_id"))null else row.getString("candidate_id"),candidate?.appointmentID?.toString())
            if(candidate!=null)assertEquals(raw,candidate.raw)
        }
    }
    @Test fun sourceIDCannotBeManufacturedFromCandidate() {
        val cases=JSONObject(fixture("relative-appointment-candidate")).getJSONArray("corroboration_cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val notification=JsonContracts.notifications(JSONObject(fixture("notifications-101")).put("items",org.json.JSONArray().put(row.getJSONObject("source"))).toString()).items.single()
            val target=RelativeAppointmentCandidate.parse(row.getString("raw"))?.corroboratedTarget(notification)
            assertEquals(row.getString("name"),if(row.isNull("target"))null else row.getInt("target"),target)
        }
    }
    @Test fun editorReviewBackKeepsRawWithoutRequestsOrMarkerEffects()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val repo=Repo(page());val m=ready(repo);runCurrent();m.open(2101,m.control);val oldCard=m.control;m.beginRoute(oldCard);val editor=m.routeControl
            assertNotNull(editor);m.editRoute("/app/calendar/501",editor);m.reviewRoute(editor);val review=m.routeControl
            assertTrue(m.routeCorroborated);assertTrue(m.routeReviewing);m.editRoute("bad",editor);m.backRoute(editor);m.openTarget(m.control);runCurrent()
            assertTrue(m.routeReviewing);assertEquals("/app/calendar/501",m.routeInput);assertEquals(0,repo.targets);assertEquals(1,repo.lists);assertTrue(m.state.selected!!.unread)
            m.backRoute(review);assertFalse(m.routeReviewing);assertEquals("/app/calendar/501",m.routeInput);m.backRoute(review);assertTrue(m.routeEditorActive)
            m.backRoute(m.routeControl);assertFalse(m.routeEditorActive);m.openTarget(oldCard);runCurrent();assertEquals(0,repo.targets)
            m.beginRoute(m.control);assertEquals("/app/calendar/501",m.routeInput);assertNotEquals(editor,m.routeControl);assertEquals(0,m.markRead.retainedAttemptCount)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun unsupportedAndMismatchedRawRemainCorrectable()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val m=ready(Repo(page()));runCurrent();m.open(2101,m.control);m.beginRoute(m.control);m.editRoute(" /app/calendar/501",m.routeControl);m.reviewRoute(m.routeControl)
            assertNull(m.routeCandidate);assertFalse(m.routeCorroborated);assertEquals(" /app/calendar/501",m.routeInput)
            m.backRoute(m.routeControl);m.editRoute("/app/calendar/502",m.routeControl);m.reviewRoute(m.routeControl);assertNotNull(m.routeCandidate);assertFalse(m.routeCorroborated)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun oldSameIDCardAndEpochCannotReviveInput()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val m=ready(Repo(page()));runCurrent();m.search("Alpha",m.control);m.open(2101,m.control);m.beginRoute(m.control);val old=m.routeControl;m.editRoute("raw",old);m.close(m.control)
            assertEquals("Alpha",m.state.query);assertEquals("",m.routeInput);m.open(2101,m.control);m.beginRoute(m.control);m.editRoute("old",old);assertEquals("",m.routeInput)
            val epoch=m.routeControl;m.reconcileOwner(101,2);m.editRoute("foreign",epoch);m.reviewRoute(epoch);assertNull(m.routeControl);assertEquals("",m.routeInput);assertNull(m.state.business)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun legacyLeadWithSameNumericIDCannotCorroborate()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val repo=Repo(page());val m=ready(repo);runCurrent();m.open(2102,m.control);m.beginRoute(m.control);m.editRoute("/app/calendar/501",m.routeControl);m.reviewRoute(m.routeControl)
            assertNotNull(m.routeCandidate);assertEquals(501,m.state.selected!!.appointmentID);assertFalse(m.routeCorroborated);assertEquals(0,repo.targets)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun rereadInvalidatesReviewBeforeNewResponseAndFailure()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var calls=0;val pending=CompletableDeferred<NotificationPage>()
            val repo=object:NotificationRepository {
                override suspend fun notifications(business:Int):NotificationPage=if(++calls==1)page() else pending.await()
                override suspend fun appointment(business:Int,id:Int):AppointmentDetail=error("No fetch")
            }
            val m=NotificationCenterViewModel(repo);m.load(101,1);runCurrent();m.open(2101,m.control);m.beginRoute(m.control);m.editRoute("/app/calendar/501",m.routeControl);m.reviewRoute(m.routeControl);val old=m.routeControl
            m.load(101,1);runCurrent();assertFalse(m.routeEditorActive);assertEquals("",m.routeInput);m.backRoute(old);m.editRoute("old",old)
            pending.completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertNull(m.routeControl);assertEquals(ReadProblem.DENIED,m.state.problem)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun routeMatchCannotClearOrRepeatUnknownMarkerAttempt()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            var calls=0;val port=object:SyntheticNotificationMarkReadPort {
                override val grants=listOf(SyntheticNotificationMarkReadGrant(101,2101,9001,true))
                override suspend fun execute(attempt:NotificationMarkReadAttempt):SyntheticNotificationMarkReadOutcome {++calls;return SyntheticNotificationMarkReadOutcome.Unknown}
            }
            val repo=Repo(page());val m=NotificationCenterViewModel(repo,port);m.load(101,1);runCurrent();m.open(2101,m.control)
            val source=m.markRead.read!!;m.markRead.prepare(source);val review=m.markRead.review!!;m.markRead.submit(review);runCurrent();assertEquals(NotificationMarkReadPhase.UNKNOWN,m.markRead.submission!!.phase)
            m.beginRoute(m.control);m.editRoute("/app/calendar/501",m.routeControl);m.reviewRoute(m.routeControl);assertTrue(m.routeCorroborated);assertNull(m.markRead.read);assertEquals(1,m.markRead.retainedAttemptCount)
            m.backRoute(m.routeControl);m.backRoute(m.routeControl);assertTrue(m.markRead.blocked);assertFalse(m.markRead.canPrepare);m.markRead.submit(review);runCurrent();assertEquals(1,calls);assertTrue(m.state.selected!!.unread)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun missingOwnerAndPendingTargetCannotStartRoute()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val pending=CompletableDeferred<AppointmentDetail>();val repo=object:NotificationRepository {
                override suspend fun notifications(business:Int)=page()
                override suspend fun appointment(business:Int,id:Int)=pending.await()
            }
            val m=NotificationCenterViewModel(repo);m.beginRoute(null);assertFalse(m.routeEditorActive);m.load(101,1);runCurrent();m.open(2101,m.control);m.openTarget(m.control);runCurrent();m.beginRoute(m.control);assertFalse(m.routeEditorActive)
            pending.completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();assertFalse(m.routeEditorActive)
        } finally {Dispatchers.resetMain()}
    }
}
