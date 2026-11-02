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
class InboxConversationFilesTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun repository()=APIReadRepository(ReadTransport {q->val name=if(q.path=="/api/mobile/v1/inbox/")"inbox-${q.query["business"]}" else "inbox-${q.query["business"]}-${q.path.trimEnd('/').substringAfterLast('/')}";ReadResponse(200,fixture(name))})
    private fun files(log:MutableList<ReadRequest> = mutableListOf()):InboxConversationFilesRepository {val transport=FixtureInboxConversationFilesTransport.fromJSON(fixture("inbox-conversation-files"));return APIInboxConversationFilesRepository(ReadTransport {q->log+=q;transport.get(q)})}
    private class Held:InboxConversationFilesRepository {val pending=mutableListOf<CompletableDeferred<List<InboxConversationFileMetadata>>>();override suspend fun files(context:InboxConversationFilesContext)=CompletableDeferred<List<InboxConversationFileMetadata>>().also {pending+=it}.await()}
    private class UnknownReply(override val grants:List<SyntheticInboxReplyGrant>):SyntheticInboxReplyPort {override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome=SyntheticInboxReplyOutcome.Unknown}
    @Test fun sharedGenericDetailScopeRawStrictMissingEmptyAndStatusContract()=runTest {
        val catalog=JSONObject(fixture("inbox-conversation-files"));val cases=catalog.getJSONArray("cases")
        for(i in 0 until cases.length()) {val row=cases.getJSONObject(i);val c=row.getJSONObject("context");val context=InboxConversationFilesContext(c.getInt("business"),c.getInt("conversation"),c.getInt("epoch"),c.getInt("revision"));val rows=InboxConversationFileMetadata.decode(row.getString("response_json"),context);assertEquals(row.getString("name"),row.getBoolean("valid"),rows!=null);rows?.forEach {assertTrue(it.validFor(context));assertFalse(it.toString().contains("example.invalid"))}}
        val log=mutableListOf<ReadRequest>();val context=InboxConversationFilesContext(101,901,1,1);val rows=files(log).files(context);assertEquals(listOf(ReadRequest("/api/inbox/conversations/901/")),log);assertEquals(2,rows.size);assertEquals(4294967296L,rows[0].size);assertEquals(0L,rows[1].size);assertEquals("",rows[1].contentType)
        val raw=catalog.getJSONArray("reads").getJSONObject(0).getString("response_json");val changed=InboxConversationFileMetadata.decode(raw.replace("e\u0301.txt","é.txt"),context)!!;assertNotEquals(rows[1],changed[1]);assertEquals(rows[0],changed[0])
        for((status,problem) in listOf(403 to ReadProblem.DENIED,404 to ReadProblem.NOT_FOUND,503 to ReadProblem.UNAVAILABLE)) {try {APIInboxConversationFilesRepository(ReadTransport {ReadResponse(status,"")}).files(context);fail("Metadata status accepted")}catch(error:ReadException){assertEquals(problem,error.problem)}}
        try {files().files(InboxConversationFilesContext(202,901,1,1));fail("Foreign generic response accepted")}catch(error:ReadException){assertEquals(ReadProblem.INVALID_PAYLOAD,error.problem)}
    }
    @Test fun actualParentManualReadStablePresentationStaleRowsAndPeers()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val log=mutableListOf<ReadRequest>();val m=InboxViewModel(repository(),files=files(log))
        try {
            m.load(101,77);runCurrent();assertNull(m.filesEntryControl);m.open(901);runCurrent();val child=m.fileMetadata!!;val entry=m.filesEntryControl!!;val oldReturn=m.returnControl;val parent=m.control;val source=m.threadSelection;val original=m.state.thread;val client=m.clientLinks?.entryControl;val handoff=m.handoff.entryControl;val context=m.reply.state.context!!
            assertTrue(log.isEmpty());m.openFiles(entry);val presentation=m.filesPresentationControl!!;val before=child.control;assertTrue(child.presented);assertFalse(child.loaded);assertFalse(child.loading);assertNull(m.filesEntryControl)
            m.openFiles(entry);m.backToThreadList(oldReturn);m.openReply(context,parent);m.openClientEntry(client,m.control);m.openHandoff(handoff,m.control);m.openReply(context,m.control);assertEquals(source,m.threadSelection);assertNull(m.reply.control);assertNull(m.handoff.control);assertNull(m.clientLinks?.state?.selectedID)
            child.load(child.control);val rows=child.items;val loaded=child.control;assertEquals(listOf(ReadRequest("/api/inbox/conversations/901/")),log);assertEquals(2,rows.size);assertEquals(presentation,m.filesPresentationControl);assertEquals(original,m.state.thread)
            child.select(rows[0],before);assertNull(child.selected);child.select(rows[0],loaded);val oldRow=child.control;assertEquals(rows[0],child.selected);child.back(oldRow);child.load(child.control);child.select(rows[0],loaded);assertNull(child.selected);child.select(child.items[1],child.control);val second=child.selected;child.back(oldRow);assertEquals(second,child.selected)
            m.closeFiles(presentation);assertFalse(child.presented);assertTrue(child.items.isEmpty());assertNotNull(m.filesEntryControl);m.openFiles(m.filesEntryControl);val reopened=m.filesPresentationControl;m.closeFiles(presentation);m.openFiles(entry);assertEquals(reopened,m.filesPresentationControl);m.closeFiles(reopened)
            m.openReply(context,m.control);m.openFiles(m.filesEntryControl);assertFalse(child.presented);assertNull(m.filesEntryControl);assertNotNull(m.reply.control);m.reply.close(m.reply.returnControl)
            val none=InboxViewModel(repository());none.load(101,1);runCurrent();none.open(901);runCurrent();assertNull(none.fileMetadata);assertNull(none.filesEntryControl);none.viewModelScope.cancel()
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateForeignDuplicateDenialEmptyAndUnknownReplyAreIndependent()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val held=Held();val port=UnknownReply(FixtureInboxReplyPort(fixture("inbox-reply-outcome")).grants);val m=InboxViewModel(repository(),replySubmission=port,files=held)
        try {
            val rows=files().files(InboxConversationFilesContext(101,901,1,1));m.load(101,80);runCurrent();m.open(901);runCurrent();val child=m.fileMetadata!!;m.openFiles(m.filesEntryControl);val first=m.filesPresentationControl!!;val pending=launch {child.load(child.control)};runCurrent();m.closeFiles(first);m.openReply(m.reply.state.context!!,m.control);val reply=m.reply.control;held.pending[0].complete(rows);pending.join();m.closeFiles(first);assertEquals(reply,m.reply.control);assertTrue(child.items.isEmpty());assertFalse(child.presented)
            m.reply.close(m.reply.returnControl);m.openFiles(m.filesEntryControl);val denied=launch {child.load(child.control)};runCurrent();held.pending[1].completeExceptionally(ReadException(ReadProblem.DENIED));denied.join();assertEquals(ReadProblem.DENIED,child.failure);assertFalse(child.loaded);assertTrue(child.items.isEmpty())
            val retry=launch {child.load(child.control)};runCurrent();m.load(202,81);runCurrent();m.open(951);runCurrent();val other=m.filesEntryControl;held.pending[2].complete(rows);retry.join();assertEquals(other,m.filesEntryControl);assertEquals(202,child.context!!.business);assertFalse(child.presented);assertTrue(child.items.isEmpty())
            m.load(101,82);runCurrent();m.open(901);runCurrent();m.closeFiles(first);assertFalse(child.presented);m.openFiles(m.filesEntryControl)
            val foreign=files().files(InboxConversationFilesContext(202,951,1,1));val wrong=launch {child.load(child.control)};runCurrent();held.pending[3].complete(foreign);wrong.join();assertEquals(ReadProblem.INVALID_PAYLOAD,child.failure);assertTrue(child.items.isEmpty());val duplicate=launch {child.load(child.control)};runCurrent();held.pending[4].complete(listOf(rows[0],rows[0]));duplicate.join();assertEquals(ReadProblem.INVALID_PAYLOAD,child.failure)
            val empty=launch {child.load(child.control)};runCurrent();held.pending[5].complete(emptyList());empty.join();assertTrue(child.loaded);assertNull(child.failure);assertTrue(child.items.isEmpty());m.closeFiles(m.filesPresentationControl)
            m.openReply(m.reply.state.context!!,m.control);m.reply.update(" Retained unknown reply ",m.reply.inputControl);m.reply.prepare(m.reply.control);m.reply.submit(m.reply.state.review!!,m.reply.control);runCurrent();val record=m.reply.submission!!;assertEquals(InboxReplyPhase.UNKNOWN,record.phase);m.reply.close(m.reply.returnControl);m.openFiles(m.filesEntryControl);assertTrue(child.presented);val metadata=launch {child.load(child.control)};runCurrent();held.pending[6].complete(rows);metadata.join();m.closeFiles(m.filesPresentationControl);assertTrue(m.reply.submissionBlocked);assertEquals(record,m.reply.submission);assertEquals(1,m.reply.retainedAttemptCount)
        } finally {m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
