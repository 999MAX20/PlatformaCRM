package kz.zani.mobile

import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.data.NotificationRepository
import kz.zani.mobile.ui.NotificationCenterViewModel
import kz.zani.mobile.ui.NotificationMarkUnreadModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class NotificationMarkUnreadTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page()=JsonContracts.notifications(fixture("notifications-101"))
    private fun source(epoch:Int=1)=NotificationMarkUnreadSource(NotificationMarkUnreadContext(101,2102,epoch),1,page().items.first {it.id==2102})
    private class UnreadPort:SyntheticNotificationMarkUnreadPort {
        override val grants=listOf(SyntheticNotificationMarkUnreadGrant(101,2102,9001,true))
        val attempts=mutableListOf<NotificationMarkUnreadAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticNotificationMarkUnreadOutcome>>()
        override suspend fun execute(attempt:NotificationMarkUnreadAttempt):SyntheticNotificationMarkUnreadOutcome {attempts+=attempt;return CompletableDeferred<SyntheticNotificationMarkUnreadOutcome>().also {pending+=it}.await()}
    }
    private class ReadPort:SyntheticNotificationMarkReadPort {
        override val grants=listOf(SyntheticNotificationMarkReadGrant(101,2102,9001,true));var calls=0
        override suspend fun execute(attempt:NotificationMarkReadAttempt):SyntheticNotificationMarkReadOutcome {++calls;return SyntheticNotificationMarkReadOutcome.Unknown}
    }
    private class Repo(val page:NotificationPage):NotificationRepository {
        var gets=0;var targets=0
        override suspend fun notifications(business:Int):NotificationPage {++gets;return page}
        override suspend fun appointment(business:Int,id:Int):AppointmentDetail {++targets;error("No route fetch")}
    }
    private fun reply()=JsonContracts.notificationMarkUnreadReply(JSONObject(fixture("notification-mark-unread")).getJSONArray("validation_cases").getJSONObject(0).getJSONObject("reply").toString())
    @Test fun exactGenericResponsesRejectMobileEnvelopeAndMalformedMarker() {
        val rows=JSONObject(fixture("notification-mark-unread")).getJSONArray("validation_cases")
        for(i in 0 until rows.length()) {
            val row=rows.getJSONObject(i);val n=JsonContracts.notifications(JSONObject(fixture("notifications-101")).put("items",org.json.JSONArray().put(row.getJSONObject("source"))).toString()).items.single()
            val s=source().copy(notification=n);val grant=SyntheticNotificationMarkUnreadGrant(101,2102,9001,true);val auth=grant.authorization(s.context)!!;val ledger=NotificationMarkUnreadLedger();val attempt=ledger.begin(NotificationMarkUnreadReview(s,1),auth)!!
            val decoded=runCatching {JsonContracts.notificationMarkUnreadReply(row.getJSONObject("reply").toString())};assertEquals(row.getString("name"),row.getBoolean("decode"),decoded.isSuccess)
            ledger.complete(attempt,decoded.fold({SyntheticNotificationMarkUnreadOutcome.Response(row.getInt("status"),it)},{SyntheticNotificationMarkUnreadOutcome.Unknown}))
            assertEquals(row.getString("name"),if(row.getBoolean("confirmed"))NotificationMarkUnreadPhase.CONFIRMED else NotificationMarkUnreadPhase.UNKNOWN,ledger.records.single().phase)
            assertEquals(s,ledger.records.single().attempt.review.source);assertEquals(row.getBoolean("confirmed"),ledger.acknowledge(auth))
        }
    }
    @Test fun independentUpdateGrantRequiredAndUnknownSurvivesEpoch() {
        val s=source();assertNull(SyntheticNotificationMarkUnreadGrant(101,2102,9001,false).authorization(s.context));val grant=SyntheticNotificationMarkUnreadGrant(101,2102,9001,true);val auth=grant.authorization(s.context)!!
        assertNull(grant.authorization(s.context.copy(business=202)));assertNull(grant.copy(actor=0).authorization(s.context));val model=NotificationMarkUnreadModel();model.bind(s);assertFalse(model.canPrepare)
        val ledger=NotificationMarkUnreadLedger();val attempt=ledger.begin(NotificationMarkUnreadReview(s,1),auth)!!;assertNull(ledger.begin(attempt.review,auth));ledger.complete(attempt,SyntheticNotificationMarkUnreadOutcome.Unknown)
        val next=source(2);val nextAuth=grant.authorization(next.context)!!;assertTrue(ledger.blocked(next.context));assertNull(ledger.visible(nextAuth));assertFalse(ledger.acknowledge(nextAuth));assertFalse(ledger.blocked(s.context.copy(notification=2101)))
    }
    @Test fun staleReviewPendingDoubleClickAndConfirmedAckRequireFreshReview()=runTest {
        val port=UnreadPort();val m=NotificationMarkUnreadModel(port,this);val s=source();m.bind(s);m.prepare(s);val old=m.review!!;m.back(old);m.prepare(s);val review=m.review!!;m.submit(old);assertTrue(port.attempts.isEmpty())
        val send=launch {m.submit(review)};runCurrent();m.submit(review);m.back(review);assertEquals(1,port.attempts.size);assertEquals(review,m.review);port.pending[0].complete(SyntheticNotificationMarkUnreadOutcome.Response(200,reply()));send.join()
        assertEquals(NotificationMarkUnreadPhase.CONFIRMED,m.submission!!.phase);m.acknowledge(s,99);assertTrue(m.blocked);m.acknowledge(s,1);assertTrue(m.canPrepare);assertNull(m.review);assertEquals(1,m.retainedAttemptCount);m.submit(review);assertEquals(1,port.attempts.size)
    }
    @Test fun noWriteUnknownAndLateOutcomeDoNotEnableReplay()=runTest {
        val port=UnreadPort();val m=NotificationMarkUnreadModel(port,this);val s=source();m.bind(s);m.prepare(s);val first=m.review!!;val send=launch {m.submit(first)};runCurrent();port.pending[0].complete(SyntheticNotificationMarkUnreadOutcome.RejectedWithoutWrite);send.join()
        assertFalse(m.canPrepare);m.acknowledge(s,1);m.prepare(s);val current=m.review!!;val late=launch {m.submit(current)};runCurrent();m.bind(null);m.bind(source(2));port.pending[1].complete(SyntheticNotificationMarkUnreadOutcome.Unknown);late.join()
        assertTrue(m.blocked);assertNull(m.submission);assertEquals(2,m.retainedAttemptCount);m.submit(current);m.acknowledge(source(2),2);assertTrue(m.blocked);assertEquals(2,port.attempts.size)
    }
    @Test fun parentUnreadBlocksReadAndInvalidatesPreparedPeerReview()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val repo=Repo(page());val port=UnreadPort();val read=ReadPort();val parent=NotificationCenterViewModel(repo,read,port);parent.load(101,1);runCurrent();parent.open(2102,parent.control)
            val s=parent.markUnread.read!!;val rs=parent.markRead.read!!;parent.markRead.prepare(rs);val oldRead=parent.markRead.review!!;parent.markUnread.prepare(s);val review=parent.markUnread.review!!
            val send=launch {parent.markUnread.submit(review)};runCurrent();parent.markRead.submit(oldRead);assertEquals(0,read.calls);assertTrue(parent.markRead.blocked);assertNull(parent.markRead.review)
            port.pending[0].complete(SyntheticNotificationMarkUnreadOutcome.Response(200,reply()));send.join();assertEquals(page().items,parent.state.items);assertNotNull(parent.state.selected!!.readAt);assertEquals(1,repo.gets)
            parent.markUnread.acknowledge(s,1);parent.markRead.submit(oldRead);assertEquals(0,read.calls);assertTrue(parent.markRead.canPrepare);assertTrue(parent.markUnread.canPrepare)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun readUnknownBlocksUnreadSymmetrically()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val port=UnreadPort();val read=ReadPort();val parent=NotificationCenterViewModel(Repo(page()),read,port);parent.load(101,1);runCurrent();parent.open(2102,parent.control)
            val s=parent.markUnread.read!!;parent.markUnread.prepare(s);val old=parent.markUnread.review!!;val rs=parent.markRead.read!!;parent.markRead.prepare(rs);parent.markRead.submit(parent.markRead.review!!);parent.markUnread.submit(old)
            assertTrue(parent.markUnread.blocked);assertNull(parent.markUnread.review);assertTrue(port.attempts.isEmpty());assertEquals(1,read.calls);assertFalse(parent.markUnread.canPrepare)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun routeAndRereadCannotAcknowledgeUnknownOrMutateSource()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val repo=Repo(page());val port=UnreadPort();val parent=NotificationCenterViewModel(repo,ReadPort(),port);parent.load(101,1);runCurrent();parent.open(2102,parent.control);val m=parent.markUnread;val s=m.read!!;m.prepare(s);val review=m.review!!
            val send=launch {m.submit(review)};runCurrent();parent.close(parent.control);parent.load(101,2);runCurrent();parent.open(2102,parent.control);port.pending[0].complete(SyntheticNotificationMarkUnreadOutcome.Unknown);send.join()
            assertTrue(m.blocked);assertTrue(parent.markRead.blocked);assertNull(m.submission);parent.beginRoute(parent.control);parent.editRoute("/app/calendar/501",parent.routeControl);parent.reviewRoute(parent.routeControl);assertNull(m.read);assertEquals(1,m.retainedAttemptCount)
            parent.backRoute(parent.routeControl);parent.backRoute(parent.routeControl);assertTrue(m.blocked);assertTrue(parent.markRead.blocked);assertEquals(page().items,parent.state.items);assertEquals(2,repo.gets);assertEquals(0,repo.targets)
        } finally {Dispatchers.resetMain()}
    }
    @Test fun cancellationAfterDispatchRetainsUnknown()=runTest {
        val port=UnreadPort();val m=NotificationMarkUnreadModel(port,this);val s=source();m.bind(s);m.prepare(s);val review=m.review!!;val send=launch {m.submit(review)};runCurrent();send.cancelAndJoin()
        assertEquals(NotificationMarkUnreadPhase.UNKNOWN,m.submission!!.phase);assertTrue(m.blocked);assertEquals(review,m.submission!!.attempt.review);assertEquals(1,m.retainedAttemptCount)
    }
    @Test fun siblingUnknownDoesNotBlockDifferentNotificationOrBusiness()=runTest {
        val port=UnreadPort();val m=NotificationMarkUnreadModel(port,this);val s=source();m.bind(s);m.prepare(s);val send=launch {m.submit(m.review!!)};runCurrent();port.pending[0].complete(SyntheticNotificationMarkUnreadOutcome.Unknown);send.join()
        assertTrue(m.blocks(s.context));assertFalse(m.blocks(s.context.copy(notification=2101)));assertFalse(m.blocks(s.context.copy(business=202)))
    }
}
