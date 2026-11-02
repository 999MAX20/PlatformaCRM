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
class ReplyDraftTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() }
    private val a=ReplyDraftContext(101,901,4)
    @Test fun stripsExactlySourceWhitespaceAndRetainsRawInput() {
        val rows=JSONObject(fixture("reply-draft-validation")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val raw=row.getString("raw");val stripped=row.getString("stripped");val s=ReplyDraftSession()
            s.bind(a,true);s.open(a);val token=s.state.selection!!;s.update(raw,token)
            assertEquals(stripped,ReplyDraftText.stripped(raw));assertEquals(stripped.isNotEmpty(),s.prepare(token));assertEquals(raw,s.state.text)
            if(stripped.isNotEmpty()) assertEquals(stripped,s.state.review!!.text) else assertTrue(s.state.emptyError)
        }
    }
    @Test fun threadBuffersRestoreOnlyAfterVerifiedReadAndNeverMix() {
        val s=ReplyDraftSession();s.bind(a,true);s.open(a);s.update("First",s.state.selection!!);s.pause()
        assertEquals("",s.state.text);s.bind(a,false);assertFalse(s.open(a));s.bind(a,true);assertEquals("First",s.state.text)
        val b=ReplyDraftContext(101,902,4);s.bind(b,true);assertEquals("",s.state.text);s.open(b);s.update("Second",s.state.selection!!)
        s.bind(a,true);assertEquals("First",s.state.text);s.open(a);s.discard(s.state.selection!!);s.bind(b,true);assertEquals("Second",s.state.text)
        s.bind(a,true);assertEquals("",s.state.text)
    }
    @Test fun previewBackCloseAndStaleCallbacksPreserveCurrentRawDraft() {
        val s=ReplyDraftSession();s.bind(a,true);s.open(a);val old=s.state.selection!!;s.update("  Text  ",old);s.prepare(old)
        s.update("late",old);assertEquals("Text",s.state.review!!.text);s.back(old);assertEquals("  Text  ",s.state.text)
        s.back(old);assertNull(s.state.selection);s.open(a);val current=s.state.selection!!;s.discard(old);s.update("late",old)
        assertEquals(current,s.state.selection);assertEquals("  Text  ",s.state.text)
    }
    @Test fun businessEpochAndClearInvalidateAllPrivateBuffers() {
        val s=ReplyDraftSession();s.bind(a,true);s.open(a);val old=s.state.selection!!;s.update("Private",old)
        s.bind(a.copy(epoch=5),true);assertEquals("",s.state.text);s.update("old",old);assertEquals("",s.state.text)
        s.retainOwner(202,6);s.bind(a,true);assertEquals("",s.state.text);s.clear();assertNull(s.state.context)
        s.bind(a.copy(business=0),true);assertFalse(s.state.available)
    }
    @Test fun sourceStatusIsTypedAndOnlyVerifiedOpenCanPrepare() {
        val json=JSONObject(fixture("inbox-101-901"));val m=ReplyDraftModel()
        for(status in listOf("closed","archived","unknown")) {json.getJSONObject("details").put("status",status);m.verified(JsonContracts.thread(json.toString()),101,901,4);m.open(a);assertNull(m.state.selection)}
        json.getJSONObject("details").remove("status");m.verified(JsonContracts.thread(json.toString()),101,901,4);assertFalse(m.state.available)
        json.getJSONObject("details").put("status",1)
        try {JsonContracts.thread(json.toString());fail("Malformed status accepted")} catch(e: ReadException) {assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
    }
    @Test fun inboxOwnerDraftHasNoRequestsMessagesOrUnreadEffectsAndSwitchInvalidatesPending()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        val calls=mutableListOf<String>();val pending=CompletableDeferred<InboxThread>();var hold=false
        val repo=object: InboxRepository {
            override suspend fun inbox(business: Int): InboxList {calls+="list";return JsonContracts.inbox(fixture("inbox-$business"))}
            override suspend fun thread(business: Int,id: Int): InboxThread {calls+="thread";return if(hold) pending.await() else JsonContracts.thread(fixture("inbox-$business-$id"))}
        }
        val model=InboxViewModel(repo)
        try {
            model.load(101,4);runCurrent();model.open(901);runCurrent();val before=calls.size;val thread=model.state.thread!!
            model.reply.open(a);val token=model.reply.state.selection!!;model.reply.update("  Local  ",token);model.reply.prepare(token)
            assertEquals(ReplyDraftPhase.REVIEW,model.reply.state.phase);assertEquals(before,calls.size);assertEquals(thread,model.state.thread)
            model.reply.back(token);model.reply.back(token);model.back();model.open(902);runCurrent();assertEquals("",model.reply.state.text)
            model.open(901);runCurrent();assertEquals("  Local  ",model.reply.state.text)
            hold=true;model.open(901);runCurrent();model.load(202,5);runCurrent();pending.complete(thread);runCurrent()
            assertEquals(202,model.state.business);assertNull(model.state.thread);assertNull(model.reply.state.context)
        } finally {model.back();model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
}
