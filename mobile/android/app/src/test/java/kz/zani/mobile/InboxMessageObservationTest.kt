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
class InboxMessageObservationTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun context(c:JSONObject)=InboxMessageFilesContext(c.getInt("business"),c.getInt("conversation"),c.getInt("message"),c.getInt("epoch"),c.getInt("revision"),c.getInt("limit"))
    private fun repository()=APIReadRepository(ReadTransport {q->val name=if(q.path=="/api/mobile/v1/inbox/")"inbox-${q.query["business"]}" else "inbox-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}";ReadResponse(200,fixture(name))})
    private fun verify(o:InboxMessageObservation,row:JSONObject) {
        val wanted=row.getJSONObject("observed")
        for((key,value) in listOf("status" to o.status,"sent_at" to o.sentAt,"delivered_at" to o.deliveredAt,"read_at" to o.readAt)) {
            val w=wanted.getJSONObject(key)
            when(value){InboxObservedText.Missing->assertEquals("missing",w.getString("kind"));InboxObservedText.Null->assertEquals("null",w.getString("kind"));is InboxObservedText.Value->{assertEquals("value",w.getString("kind"));assertEquals(w.getString("raw"),value.raw)}}
        }
        assertEquals(InboxMessageState.from(row.getString("state")),o.state)
    }
    private class Held:InboxMessageFilesRepository {
        val anchors=mutableListOf<CompletableDeferred<InboxFilesConversationAnchor>>();val windows=mutableListOf<CompletableDeferred<InboxMessageFileWindow>>()
        override suspend fun anchor(context:InboxMessageFilesContext)=CompletableDeferred<InboxFilesConversationAnchor>().also {anchors+=it}.await()
        override suspend fun messages(context:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor)=CompletableDeferred<InboxMessageFileWindow>().also {windows+=it}.await()
    }
    private class UnknownReply(override val grants:List<SyntheticInboxReplyGrant>):SyntheticInboxReplyPort {override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome=SyntheticInboxReplyOutcome.Unknown}
    @Test fun sharedStrictPresenceRawUnknownAndAllRowObservationContract() {
        val catalog=JSONObject(fixture("inbox-message-observations"));val cases=catalog.getJSONArray("cases")
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val c=context(row.getJSONObject("context"));val o=InboxMessageObservation.decode(row.getString("response_json"),c);assertEquals(row.getString("name"),row.getBoolean("valid"),o!=null);o?.let {assertTrue(it.validFor(c));verify(it,row)}}
        val windows=catalog.getJSONArray("window_cases")
        for(i in 0 until windows.length()) {val row=windows.getJSONObject(i);val c=context(row.getJSONObject("context"));val result=try {val w=InboxMessageFileWindow.decode(row.getString("response_json"),c);assertTrue(w.validFor(c));verify(w.observation,row);"valid"}catch(e:ReadException){if(e.problem==ReadProblem.UNAVAILABLE)"unavailable" else "invalidPayload"};assertEquals(row.getString("name"),row.getString("expected"),result)}
        val pairs=catalog.getJSONArray("identity_pairs");val c=InboxMessageFilesContext(101,901,9011,1,1,30)
        for(i in 0 until pairs.length()) {val row=pairs.getJSONObject(i);assertEquals(row.getString("name"),row.getBoolean("same"),InboxMessageObservation.decode(row.getJSONObject("left").toString(),c)==InboxMessageObservation.decode(row.getJSONObject("right").toString(),c))}
    }
    @Test fun sameWindowActualParentRawRereadAndRetainedUnknownAreIndependent()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val catalog=JSONObject(fixture("inbox-message-observations"));var page=0;val log=mutableListOf<ReadRequest>();val base=FixtureInboxMessageFilesTransport.fromJSON(fixture("inbox-message-files"));val repo=APIInboxMessageFilesRepository(ReadTransport {q->log+=q;if(q.path=="/api/inbox/conversations/901/messages/"){assertEquals(mapOf("limit" to "30"),q.query);ReadResponse(200,catalog.getJSONArray("host_pages").getString(page))}else base.get(q)})
        val port=UnknownReply(FixtureInboxReplyPort(fixture("inbox-reply-outcome")).grants);val m=InboxViewModel(repository(),replySubmission=port,messageFiles=repo)
        try {
            m.load(101,97);runCurrent();m.open(901);runCurrent();val child=m.messageMetadata!!;val row=m.state.thread!!.messages[0];val original=m.state.thread;m.openMessageFiles(m.messageFilesEntryControl(row));val presentation=m.messageFilesPresentationControl;assertTrue(log.isEmpty());assertNull(child.window);child.load(child.control);val first=child.window!!.observation
            assertEquals(InboxMessageState.UNKNOWN,first.state);assertEquals(InboxObservedText.Value("provider_future"),first.status);assertEquals(InboxObservedText.Value("2026-10-28T04:20:00.000000Z"),first.sentAt);assertEquals(InboxObservedText.Value("2026-10-28T10:10:00+06:00"),first.deliveredAt);assertEquals(InboxObservedText.Value(" raw-read-observation "),first.readAt);assertEquals(original,m.state.thread);assertEquals(2,child.window!!.items.size)
            child.select(child.window!!.items[0],child.control);assertEquals(first,child.window!!.observation);child.back(child.control);val old=child.control;page=1;child.load(child.control);child.select(child.window!!.items[0],old);assertNull(child.selected);val second=child.window!!.observation;assertEquals(InboxMessageState.SENT,second.state);assertEquals(InboxObservedText.Null,second.deliveredAt);assertEquals(InboxObservedText.Missing,second.readAt);assertNotEquals(first.sentAt,second.sentAt);assertEquals(presentation,m.messageFilesPresentationControl);assertEquals(4,log.size);m.closeMessageFiles(presentation);assertNull(child.window)
            m.openReply(m.reply.state.context!!,m.control);m.reply.update(" Retained unknown observations ",m.reply.inputControl);m.reply.prepare(m.reply.control);m.reply.submit(m.reply.state.review!!,m.reply.control);runCurrent();val record=m.reply.submission!!;assertEquals(InboxReplyPhase.UNKNOWN,record.phase);m.reply.close(m.reply.returnControl);m.openMessageFiles(m.messageFilesEntryControl(row));child.load(child.control);assertEquals(InboxMessageState.SENT,child.window!!.observation.state);assertEquals(record,m.reply.submission);assertTrue(m.reply.submissionBlocked);assertEquals(1,m.reply.retainedAttemptCount);assertEquals(original,m.state.thread);m.closeMessageFiles(m.messageFilesPresentationControl);m.retryThread(m.threadSelection);runCurrent();assertEquals(record,m.reply.submission);assertTrue(m.reply.submissionBlocked);assertNull(child.window)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateObservationWindowCannotRestoreOwnerOrDisplacePeerInput()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val held=Held();val m=InboxViewModel(repository(),messageFiles=held);val base=APIInboxMessageFilesRepository(FixtureInboxMessageFilesTransport.fromJSON(fixture("inbox-message-files")));val catalog=JSONObject(fixture("inbox-message-observations"))
        try {
            m.load(101,98);runCurrent();m.open(901);runCurrent();val child=m.messageMetadata!!;m.openMessageFiles(m.messageFilesEntryControl(m.state.thread!!.messages[0]));val c=child.context!!;val job=launch {child.load(child.control)};runCurrent();held.anchors[0].complete(base.anchor(c));runCurrent();assertEquals(1,held.windows.size);m.closeMessageFiles(m.messageFilesPresentationControl);m.openReply(m.reply.state.context!!,m.control);m.reply.update(" Current peer input ",m.reply.inputControl);val peer=m.reply.control;held.windows[0].complete(InboxMessageFileWindow.decode(catalog.getJSONArray("host_pages").getString(1),c));job.join();assertNull(child.window);assertFalse(child.presented);assertEquals(peer,m.reply.control);assertEquals(" Current peer input ",m.reply.state.text)
            m.reply.close(m.reply.returnControl);m.openMessageFiles(m.messageFilesEntryControl(m.state.thread!!.messages[0]));val c2=child.context!!;val changing=launch {child.load(child.control)};runCurrent();held.anchors[1].complete(base.anchor(c2));runCurrent();m.load(202,99);runCurrent();m.open(951);runCurrent();held.windows[1].complete(InboxMessageFileWindow.decode(catalog.getJSONArray("host_pages").getString(0),c2));changing.join();assertNull(child.window);assertFalse(child.presented);assertEquals(202,child.owner!!.read.business)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
