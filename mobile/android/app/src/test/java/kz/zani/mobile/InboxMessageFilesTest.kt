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
class InboxMessageFilesTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun repository()=APIReadRepository(ReadTransport {q->val name=if(q.path=="/api/mobile/v1/inbox/")"inbox-${q.query["business"]}" else "inbox-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}";ReadResponse(200,fixture(name))})
    private fun files(log:MutableList<ReadRequest> = mutableListOf()):InboxMessageFilesRepository {val source=FixtureInboxMessageFilesTransport.fromJSON(fixture("inbox-message-files"));return APIInboxMessageFilesRepository(ReadTransport {q->log+=q;source.get(q)})}
    private fun conversationFiles()=APIInboxConversationFilesRepository(FixtureInboxConversationFilesTransport.fromJSON(fixture("inbox-conversation-files")))
    private fun message(o:JSONObject):InboxMessage {
        fun text(key:String)=if(o.has(key) && !o.isNull(key))o.getString(key) else null
        return InboxMessage(o.getInt("id"),o.getInt("conversation_id"),text("direction"),text("sender_type"),text("text"),text("created_at"),InboxMessageState.from(o.opt("status")))
    }
    private fun context(c:JSONObject)=InboxMessageFilesContext(c.getInt("business"),c.getInt("conversation"),c.getInt("message"),c.getInt("epoch"),c.getInt("revision"),c.getInt("limit"))
    private class Held:InboxMessageFilesRepository {
        val anchors=mutableListOf<CompletableDeferred<InboxFilesConversationAnchor>>();val windows=mutableListOf<CompletableDeferred<InboxMessageFileWindow>>()
        override suspend fun anchor(context:InboxMessageFilesContext)=CompletableDeferred<InboxFilesConversationAnchor>().also {anchors+=it}.await()
        override suspend fun messages(context:InboxMessageFilesContext,anchor:InboxFilesConversationAnchor)=CompletableDeferred<InboxMessageFileWindow>().also {windows+=it}.await()
    }
    private class UnknownReply(override val grants:List<SyntheticInboxReplyGrant>):SyntheticInboxReplyPort {override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome=SyntheticInboxReplyOutcome.Unknown}
    @Test fun sharedAnchorFirstWindowEveryRowRawScopeAndMissingSelectedContract()=runTest {
        val catalog=JSONObject(fixture("inbox-message-files"));val anchors=catalog.getJSONArray("anchor_cases")
        for(i in 0 until anchors.length()) {val r=anchors.getJSONObject(i);val c=context(r.getJSONObject("context"));val value=InboxFilesConversationAnchor.decode(r.getString("response_json"),c);assertEquals(r.getString("name"),r.getBoolean("valid"),value!=null);value?.let {assertTrue(it.matches(c))}}
        val cases=catalog.getJSONArray("cases")
        for(i in 0 until cases.length()) {val r=cases.getJSONObject(i);val c=context(r.getJSONObject("context"));val actual=try {val w=InboxMessageFileWindow.decode(r.getString("response_json"),c);assertTrue(w.validFor(c));assertTrue(w.items.all {it.validFor(c)});"valid"}catch(e:ReadException){if(e.problem==ReadProblem.UNAVAILABLE)"unavailable" else "invalidPayload"};assertEquals(r.getString("name"),r.getString("expected"),actual)}
        val identity=catalog.getJSONArray("source_identity_cases")
        for(i in 0 until identity.length()) {val r=identity.getJSONObject(i);assertEquals(r.getString("name"),r.getBoolean("same"),InboxMessageFileSourceIdentity.same(message(r.getJSONObject("left")),message(r.getJSONObject("right"))))}
        val c=InboxMessageFilesContext(101,901,9011,1,1,30);val log=mutableListOf<ReadRequest>();val repo=files(log);val a=repo.anchor(c);val w=repo.messages(c,a);assertEquals(listOf(ReadRequest("/api/inbox/conversations/901/"),ReadRequest("/api/inbox/conversations/901/messages/",mapOf("limit" to "30"))),log);assertEquals(2,w.items.size);assertEquals(4294967296L,w.items[0].size);assertEquals(0L,w.items[1].size);assertEquals(2L,w.count);assertFalse(w.limited);assertTrue(repo.messages(c.copy(message=9012),a).items.isEmpty())
        for((status,problem) in listOf(403 to ReadProblem.DENIED,404 to ReadProblem.NOT_FOUND,503 to ReadProblem.UNAVAILABLE)) {try {APIInboxMessageFilesRepository(ReadTransport {ReadResponse(status,"")}).anchor(c);fail("Anchor status accepted")}catch(e:ReadException){assertEquals(problem,e.problem)}}
    }
    @Test fun actualParentExplicitSelectedMessageProvidedLimitStablePresentationPeersAndUnknown()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val log=mutableListOf<ReadRequest>();val port=UnknownReply(FixtureInboxReplyPort(fixture("inbox-reply-outcome")).grants);val m=InboxViewModel(repository(),replySubmission=port,files=conversationFiles(),messageFiles=files(log))
        try {
            m.load(101,88);runCurrent();m.open(901);runCurrent();val child=m.messageMetadata!!;val row=m.state.thread!!.messages[0];val other=m.state.thread!!.messages[1];val original=m.state.thread;val entry=m.messageFilesEntryControl(row)!!;val parent=m.control;val oldReturn=m.returnControl;val peers=m.filesEntryControl;val reply=m.reply.state.context!!
            assertTrue(log.isEmpty());assertEquals(m.state.thread!!.maxMessages,child.owner!!.limit);m.openMessageFiles(entry);val presentation=m.messageFilesPresentationControl!!;val before=child.control;assertEquals(row.id,child.context!!.message);assertNull(child.window);assertFalse(child.loading);assertNull(m.filesEntryControl);assertNull(m.messageFilesEntryControl(other))
            m.backToThreadList(oldReturn);m.openFiles(peers);m.openReply(reply,parent);m.openReply(reply,m.control);m.openHandoff(m.handoff.entryControl,m.control);m.openClientEntry(m.clientLinks?.entryControl,m.control);assertEquals(presentation,m.messageFilesPresentationControl);assertNull(m.reply.control);assertNull(m.handoff.control);assertNull(m.clientLinks?.state?.selectedID)
            child.load(child.control);val w=child.window!!;val loaded=child.control;assertEquals(listOf(ReadRequest("/api/inbox/conversations/901/"),ReadRequest("/api/inbox/conversations/901/messages/",mapOf("limit" to child.context!!.limit.toString()))),log);assertEquals(2,w.items.size);assertEquals(original,m.state.thread);assertEquals(presentation,m.messageFilesPresentationControl)
            child.select(w.items[0],before);assertNull(child.selected);child.select(w.items[0],loaded);val oldRow=child.control;child.back(oldRow);child.load(child.control);child.select(w.items[0],loaded);assertNull(child.selected);child.select(child.window!!.items[1],child.control);val selected=child.selected;child.back(oldRow);assertEquals(selected,child.selected)
            m.closeMessageFiles(presentation);assertNull(child.window);assertFalse(child.presented);m.openMessageFiles(m.messageFilesEntryControl(other));val second=m.messageFilesPresentationControl;m.closeMessageFiles(presentation);m.openMessageFiles(entry);assertEquals(second,m.messageFilesPresentationControl);child.load(child.control);assertTrue(child.window!!.items.isEmpty());assertNull(child.failure);m.closeMessageFiles(second)
            m.openFiles(m.filesEntryControl);assertNull(m.messageFilesEntryControl(row));assertFalse(child.presented);m.closeFiles(m.filesPresentationControl)
            m.openReply(reply,m.control);m.reply.update(" Retained metadata unknown reply ",m.reply.inputControl);m.reply.prepare(m.reply.control);m.reply.submit(m.reply.state.review!!,m.reply.control);runCurrent();val record=m.reply.submission!!;assertEquals(InboxReplyPhase.UNKNOWN,record.phase);m.reply.close(m.reply.returnControl);m.openMessageFiles(m.messageFilesEntryControl(row));child.load(child.control);m.closeMessageFiles(m.messageFilesPresentationControl);assertEquals(record,m.reply.submission);assertTrue(m.reply.submissionBlocked);assertEquals(1,m.reply.retainedAttemptCount);assertEquals(original,m.state.thread)
            val none=InboxViewModel(repository());none.load(101,1);runCurrent();none.open(901);runCurrent();assertNull(none.messageMetadata);assertNull(none.messageFilesEntryControl(none.state.thread!!.messages[0]));none.viewModelScope.cancel()
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateAnchorDoesNotIssueDependentGetLatePageABAAndTypedForeignWindowRejected()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val held=Held();val m=InboxViewModel(repository(),files=conversationFiles(),messageFiles=held);val real=files()
        try {
            m.load(101,90);runCurrent();m.open(901);runCurrent();val child=m.messageMetadata!!;val row=m.state.thread!!.messages[0];m.openMessageFiles(m.messageFilesEntryControl(row));val first=m.messageFilesPresentationControl;val c0=child.context!!;val pending=launch {child.load(child.control)};runCurrent();m.closeMessageFiles(first);m.openFiles(m.filesEntryControl);val peer=m.filesPresentationControl;held.anchors[0].complete(real.anchor(c0));pending.join();assertTrue(held.windows.isEmpty());assertEquals(peer,m.filesPresentationControl);assertFalse(child.presented);m.closeFiles(peer)
            m.openMessageFiles(m.messageFilesEntryControl(row));val c1=child.context!!;val page=launch {child.load(child.control)};runCurrent();val a=real.anchor(c1);held.anchors[1].complete(a);runCurrent();assertEquals(1,held.windows.size);m.load(202,91);runCurrent();m.open(951);runCurrent();held.windows[0].complete(real.messages(c1,a));page.join();assertFalse(child.presented);assertNull(child.window);assertEquals(202,child.owner!!.read.business)
            m.load(101,92);runCurrent();m.open(901);runCurrent();m.closeMessageFiles(first);assertFalse(child.presented);m.openMessageFiles(m.messageFilesEntryControl(m.state.thread!!.messages[0]));val current=child.context!!;val foreign=launch {child.load(child.control)};runCurrent();held.anchors[2].complete(real.anchor(InboxMessageFilesContext(202,951,9511,1,1,30)));foreign.join();assertEquals(1,held.windows.size);assertEquals(ReadProblem.INVALID_PAYLOAD,child.failure)
            val wrong=launch {child.load(child.control)};runCurrent();val good=real.anchor(current);held.anchors[3].complete(good);runCurrent();held.windows[1].complete(real.messages(current.copy(message=9012),good));wrong.join();assertEquals(ReadProblem.INVALID_PAYLOAD,child.failure);assertNull(child.window)
            val denied=launch {child.load(child.control)};runCurrent();held.anchors[4].completeExceptionally(ReadException(ReadProblem.DENIED));denied.join();assertEquals(ReadProblem.DENIED,child.failure);assertFalse(child.loading)
            val missing=launch {child.load(child.control)};runCurrent();held.anchors[5].complete(good);runCurrent();held.windows[2].completeExceptionally(ReadException(ReadProblem.UNAVAILABLE));missing.join();assertEquals(ReadProblem.UNAVAILABLE,child.failure);assertNull(child.window);assertEquals(6,held.anchors.size);assertEquals(3,held.windows.size)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
