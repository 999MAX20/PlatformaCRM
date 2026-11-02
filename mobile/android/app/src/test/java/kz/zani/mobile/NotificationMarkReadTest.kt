package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.data.NotificationRepository
import kz.zani.mobile.ui.NotificationCenterViewModel
import kz.zani.mobile.ui.NotificationMarkReadModel
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class NotificationMarkReadTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun catalog()=JSONObject(fixture("notification-mark-read"))
    private fun source(epoch:Int=1,generation:Int=1)=NotificationMarkReadSource(NotificationMarkReadContext(101,2101,epoch),generation,JsonContracts.notifications(fixture("notifications-101")).items.first())
    private val grant=SyntheticNotificationMarkReadGrant(101,2101,9001,true)
    private fun reply()=JsonContracts.notificationMarkReadReply(catalog().getJSONArray("validation_cases").getJSONObject(0).getJSONObject("reply").toString())
    private class Controlled:SyntheticNotificationMarkReadPort {
        override val grants=listOf(SyntheticNotificationMarkReadGrant(101,2101,9001,true))
        val attempts=mutableListOf<NotificationMarkReadAttempt>()
        val pending=mutableListOf<CompletableDeferred<SyntheticNotificationMarkReadOutcome>>()
        override suspend fun execute(attempt:NotificationMarkReadAttempt):SyntheticNotificationMarkReadOutcome {attempts+=attempt;return CompletableDeferred<SyntheticNotificationMarkReadOutcome>().also {pending+=it}.await()}
    }
    @Test fun sourceRequiresSeparateUpdateGrantAndKnownMarker() {
        val s=source();assertTrue(s.valid);assertNull(grant.copy(update=false).authorization(s.context));assertNull(grant.copy(actor=0).authorization(s.context))
        assertNull(grant.authorization(s.context.copy(business=202)));assertNull(grant.authorization(s.context.copy(notification=2102)));assertNull(grant.authorization(s.context.copy(epoch=0)))
        assertFalse(s.copy(notification=s.notification.copy(readMarkerPresent=false)).valid);assertFalse(s.copy(generation=0).valid)
        val m=NotificationMarkReadModel();m.bind(s);assertFalse(m.canPrepare);assertNull(m.review)
    }
    @Test fun exactResponseCasesEnforceTypesMetadataKnownReadAndAlreadyReadTimestamp() {
        val cases=catalog().getJSONArray("validation_cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val s=source().copy(notification=JsonContracts.notifications(JSONObject(fixture("notifications-101")).put("items",org.json.JSONArray().put(row.getJSONObject("source"))).toString()).items.single())
            val auth=grant.authorization(s.context)!!;val ledger=NotificationMarkReadLedger();val review=NotificationMarkReadReview(s,1);val attempt=ledger.begin(review,auth)!!
            assertNull(ledger.begin(review,auth));val decoded=runCatching {JsonContracts.notificationMarkReadReply(row.getJSONObject("reply").toString())}
            assertEquals(row.getString("name"),row.getBoolean("decode"),decoded.isSuccess)
            ledger.complete(attempt,decoded.fold({SyntheticNotificationMarkReadOutcome.Response(row.getInt("status"),it)},{SyntheticNotificationMarkReadOutcome.Unknown}))
            val expected=if(row.getBoolean("confirmed"))NotificationMarkReadPhase.CONFIRMED else NotificationMarkReadPhase.UNKNOWN
            assertEquals(row.getString("name"),expected,ledger.records.single().phase);assertEquals(s,ledger.records.single().attempt.review.source)
            assertEquals(row.getBoolean("confirmed"),ledger.acknowledge(auth));ledger.complete(attempt,SyntheticNotificationMarkReadOutcome.RejectedWithoutWrite);assertEquals(expected,ledger.records.single().phase)
        }
    }
    @Test fun unknownSurvivesEpochRereadAndOtherTargetRemainsIndependent() {
        val s=source();val auth=grant.authorization(s.context)!!;val ledger=NotificationMarkReadLedger();val a=ledger.begin(NotificationMarkReadReview(s,1),auth)!!
        ledger.complete(a,SyntheticNotificationMarkReadOutcome.Unknown);val newer=source(2,2);val nextAuth=grant.authorization(newer.context)!!
        assertTrue(ledger.blocked(newer.context));assertNull(ledger.visible(nextAuth));assertFalse(ledger.acknowledge(nextAuth));assertNull(ledger.begin(NotificationMarkReadReview(newer,2),nextAuth))
        assertFalse(ledger.blocked(newer.context.copy(business=202)));assertFalse(ledger.blocked(newer.context.copy(notification=2102)));assertEquals(s,ledger.records.single().attempt.review.source)
    }
    @Test fun modelRejectsOldReviewAndRequiresAckThenFreshReviewAfterNoWrite()=runTest {
        val port=Controlled();val m=NotificationMarkReadModel(port,this);val s=source();m.bind(s);m.prepare(s);val old=m.review!!;m.back(old);m.prepare(s);val current=m.review!!
        m.submit(old);assertTrue(port.attempts.isEmpty());val task=launch {m.submit(current)};runCurrent();m.submit(current);m.back(current);assertEquals(1,port.attempts.size);assertEquals(NotificationMarkReadPhase.PENDING,m.submission!!.phase)
        port.pending[0].complete(SyntheticNotificationMarkReadOutcome.RejectedWithoutWrite);task.join();assertFalse(m.canPrepare);m.acknowledge(s,999);assertTrue(m.blocked)
        m.acknowledge(s,1);assertNull(m.review);assertTrue(m.canPrepare);assertEquals(1,m.retainedAttemptCount);m.prepare(s);assertNotEquals(current,m.review);m.submit(current);assertEquals(1,port.attempts.size)
    }
    @Test fun parentCardConfirmationKeepsRowsCountsFiltersAndDoesNotGetAgain()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val port=Controlled();var gets=0
        val repo=object:NotificationRepository {
            override suspend fun notifications(business:Int):NotificationPage {gets++;return JsonContracts.notifications(fixture("notifications-$business"))}
            override suspend fun appointment(business:Int,id:Int):AppointmentDetail {error("Unexpected target GET")}
        }
        val parent=NotificationCenterViewModel(repo,port)
        try {
            parent.load(101,1);runCurrent();parent.filterUnread(true,false,parent.control);parent.open(2101,parent.control)
            val m=parent.markRead;val s=m.read!!;val rows=parent.state.items;val total=parent.state.total;m.prepare(s);val review=m.review!!;val send=launch {m.submit(review)};runCurrent()
            port.pending[0].complete(SyntheticNotificationMarkReadOutcome.Response(200,reply()));send.join()
            assertEquals(NotificationMarkReadPhase.CONFIRMED,m.submission!!.phase);assertEquals(rows,parent.state.items);assertEquals(total,parent.state.total);assertTrue(parent.state.unreadOnly);assertTrue(parent.state.selected!!.unread);assertEquals(1,gets)
            m.acknowledge(s,1);m.prepare(s);val old=m.review!!;val late=launch {m.submit(old)};runCurrent();parent.close(parent.control);assertNull(m.read);assertNull(m.submission)
            parent.reconcileOwner(101,2);parent.load(101,2);runCurrent();parent.open(2101,parent.control)
            port.pending[1].complete(SyntheticNotificationMarkReadOutcome.Response(200,reply()));late.join();assertTrue(m.blocked);assertNull(m.submission);assertFalse(m.canPrepare);m.submit(old);m.acknowledge(s,2);assertTrue(m.blocked);assertEquals(2,port.attempts.size);assertEquals(rows,parent.state.items);assertEquals(2,gets)
        } finally {parent.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun errorAndPostDispatchCancellationRetainUnknownInputAndAttempt()=runTest {
        val port=Controlled();val s=source();val m=NotificationMarkReadModel(port,this);m.bind(s);m.prepare(s);val review=m.review!!;val error=launch {m.submit(review)};runCurrent();port.pending[0].completeExceptionally(IllegalStateException("Synthetic failure"));error.join()
        assertEquals(NotificationMarkReadPhase.UNKNOWN,m.submission!!.phase);assertEquals(s,m.submission!!.attempt.review.source);assertFalse(m.canPrepare);m.acknowledge(s,1);assertTrue(m.blocked)
        val cancelled=NotificationMarkReadModel(port,this);cancelled.bind(s);cancelled.prepare(s);val cancelReview=cancelled.review!!;val task=launch {cancelled.submit(cancelReview)};runCurrent();task.cancelAndJoin()
        assertEquals(NotificationMarkReadPhase.UNKNOWN,cancelled.submission!!.phase);assertEquals(1,cancelled.retainedAttemptCount);assertFalse(cancelled.canPrepare)
    }
    @Test fun queuedOwnerChangeStaleSourceAndPreDispatchCancelDoNotExecute()=runTest {
        val port=Controlled();val m=NotificationMarkReadModel(port,this);val s=source();m.bind(s);m.prepare(s);val old=m.review!!;var current=true
        m.launchSubmit(old){current};current=false;runCurrent();assertTrue(port.attempts.isEmpty())
        m.bind(source(2,2));m.prepare(s);m.back(old);m.submit(old);assertNull(m.review);assertTrue(port.attempts.isEmpty());val fresh=m.read!!;m.prepare(fresh);val r=m.review!!
        val task=launch {m.submit(r)};task.cancel();runCurrent();assertEquals(0,m.retainedAttemptCount);assertTrue(port.attempts.isEmpty());assertEquals(r,m.review)
    }
}
