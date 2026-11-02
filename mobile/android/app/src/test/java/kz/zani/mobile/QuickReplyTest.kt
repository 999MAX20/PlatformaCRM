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
class QuickReplyTest {
    private fun fixture(name: String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page(business: Int=101,channel: String="website")=JsonContracts.quickReplies(fixture("quick-replies-$business-$channel"))
    private fun draft(): ReplyDraftSession=ReplyDraftSession().also {it.bind(ReplyDraftContext(101,901,60),true);it.open(it.state.context!!)}
    @Test fun insertionAndTrimMatchExecutedWebJavaScriptWithoutInterpolation() {
        val rows=JSONObject(fixture("quick-reply-insertion")).getJSONArray("cases")
        for(n in 0 until rows.length()) {
            val row=rows.getJSONObject(n);val raw=row.getString("draft");val template=row.getString("template")
            assertEquals(row.getString("trim"),SourceTextTrim.javascriptTrim(raw));assertEquals(row.getString("trim_end"),SourceTextTrim.javascriptTrimEnd(raw))
            assertEquals(row.getString("inserted"),QuickReplyInsertion.text(raw,template))
        }
    }
    @Test fun fieldsScopeOrderingSearchAndStaleFilterRowsFollowSource() {
        val d=draft();val context=QuickReplyContext(d.state.selection!!,"website");val s=QuickReplySession();assertNull(s.open(context));s.bind(context)
        val request=s.open(context)!!;val token=s.state.selection!!;assertTrue(s.state.loading);assertFalse(s.showsEmpty);s.accept(page(),request)
        assertEquals(listOf(9101,9102,9103),s.choices.map {it.template.id});val old=s.choices[0]
        s.search(" APPOINTMENTS ",token);assertEquals(listOf(9102),s.choices.map {it.template.id});assertNull(s.resolve(old))
        s.search("",token);assertNull(s.resolve(old));s.search("СИНТЕТИЧЕСКИЙ",token);assertEquals(listOf(9101,9103),s.choices.map {it.template.id})
        try {NativeRequestBuilder(java.net.URI("https://fixtures.invalid"),30000).request(ReadRequest("/api/quick-replies/"));fail("Web route enabled in native builder")} catch(e: RequestConfigurationException) {assertEquals(RequestConfigurationProblem.INVALID_PATH,e.problem)}
        s.search("{{client}}",token);assertEquals(listOf(9101),s.choices.map {it.template.id});s.close(token);assertEquals("{{client}}",s.state.query);assertTrue(s.choices.isEmpty())
    }
    @Test fun deniedEmptyPartialUnknownAndMalformedPagesNeverShowOldOrForeignChoices() {
        val d=draft();val context=QuickReplyContext(d.state.selection!!,"website");val s=QuickReplySession();s.bind(context);s.open(context);val token=s.state.selection!!
        val good=page();val row=good.items[0]
        for(bad in listOf(good.copy(items=listOf(row.copy(business=202))),good.copy(items=listOf(row.copy(channel="manual"))),good.copy(items=listOf(row.copy(isActive=false))),good.copy(items=listOf(row.copy(sortOrder=-1))),good.copy(items=listOf(row.copy(text=" \n"))),good.copy(items=listOf(row,row)),good.copy(count=-1))) {
            s.accept(bad,s.retry(token)!!);assertEquals(ReadProblem.INVALID_PAYLOAD,s.state.problem);assertTrue(s.choices.isEmpty());assertFalse(s.showsEmpty)
        }
        s.fail(ReadProblem.DENIED,s.retry(token)!!);assertEquals(ReadProblem.DENIED,s.state.problem);assertFalse(s.showsEmpty)
        s.accept(good.copy(count=51,hasNext=true),s.retry(token)!!);s.search("does-not-exist",token);assertTrue(s.state.partial);assertFalse(s.showsEmpty)
        val json=JSONObject(fixture("quick-replies-101-website"));val unknown=JsonContracts.quickReplies(json.getJSONArray("results").toString());assertTrue(unknown.partial);assertNull(unknown.count)
        json.getJSONArray("results").getJSONObject(0).put("is_active","true")
        try {JsonContracts.quickReplies(json.toString());fail("String boolean accepted")} catch(e: ReadException) {assertEquals(ReadProblem.INVALID_PAYLOAD,e.problem)}
        s.search("",token);s.accept(QuickReplyPage(emptyList(),0,false,true),s.retry(token)!!);assertTrue(s.showsEmpty)
    }
    @Test fun insertionAdvancesEditorGenerationAndBlocksOldInputDoublePickOrReviewMutation() {
        val d=draft();val old=d.state.selection!!;d.update("  Operator note \n",old);val body=page().items[0].text
        assertFalse(d.insertTemplate(" \n",old));assertTrue(d.insertTemplate(body,old));val current=d.state.selection!!;val inserted=d.state.text
        assertNotEquals(old,current);assertEquals("  Operator note\n$body",inserted);assertTrue(inserted.contains("{{client}}"))
        d.update("late",old);assertFalse(d.insertTemplate(body,old));assertEquals(inserted,d.state.text)
        d.prepare(current);assertFalse(d.insertTemplate("late template",current));d.back(current);d.close(current);d.open(d.state.context!!);assertEquals(inserted,d.state.text)
        val long="Synthetic template\n".repeat(2000);assertTrue(d.insertTemplate(long,d.state.selection!!));assertTrue(d.state.text.endsWith(long))
    }
    private inner class Source: QuickReplyRepository {
        val requests=mutableListOf<Pair<Int,String>>();var hold=false;var problem: ReadProblem?=null
        val pending=mutableListOf<CompletableDeferred<QuickReplyPage>>()
        override suspend fun quickReplies(business: Int,channel: String): QuickReplyPage {
            requests+=business to channel;problem?.let {throw ReadException(it)}
            return if(hold)CompletableDeferred<QuickReplyPage>().also {pending+=it}.await() else page(business,channel)
        }
    }
    private inner class Inbox: InboxRepository {
        val reads=mutableListOf<Pair<Int,Int?>>();var channel: String?=null
        override suspend fun inbox(business: Int): InboxList {reads+=business to null;return JsonContracts.inbox(fixture("inbox-$business"))}
        override suspend fun thread(business: Int,id: Int): InboxThread {
            reads+=business to id;val json=JSONObject(fixture("inbox-$business-$id"));channel?.let {json.getJSONObject("conversation").put("channel",it)};return JsonContracts.thread(json.toString())
        }
    }
    @Test fun actualInboxPickerCancelInsertPreviewHaveNoSendReadMarkerOrTemplateMutation()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Inbox();val source=Source();val model=InboxViewModel(repo,source)
        try {
            model.load(101,60);runCurrent();model.open(901);runCurrent();val reply=model.reply;val picker=reply.quickReplies!!;val a=ReplyDraftContext(101,901,60)
            reply.open(a);val old=reply.state.selection!!;reply.update("  Manual note  \n",old);val before=repo.reads.size;val thread=model.state.thread
            reply.openQuickReplies(old);runCurrent();assertEquals(listOf(101 to "website"),source.requests);assertEquals(before,repo.reads.size)
            val token=picker.state.selection!!;val stale=picker.choices[0];picker.search("appointments",token);assertFalse(reply.insert(stale,old))
            assertTrue(model.backReply());assertNull(picker.state.selection);assertEquals(old,reply.state.selection);assertEquals("  Manual note  \n",reply.state.text)
            reply.openQuickReplies(old);runCurrent();val choice=picker.choices[0];assertTrue(reply.insert(choice,old));val current=reply.state.selection!!
            assertNotEquals(old,current);assertEquals("  Manual note\n${choice.template.text}",reply.state.text);assertNull(picker.state.selection)
            reply.update("late input",old);assertFalse(reply.insert(choice,old));assertEquals(thread,model.state.thread);assertEquals(before,repo.reads.size)
            reply.prepare(current);val calls=source.requests.size;reply.openQuickReplies(current);runCurrent();assertEquals(calls,source.requests.size);assertNull(picker.state.context)
            reply.back(current);source.problem=ReadProblem.DENIED;reply.openQuickReplies(current);runCurrent();assertEquals(ReadProblem.DENIED,picker.state.problem);assertEquals("  Manual note\n${choice.template.text}",reply.state.text)
            val denied=picker.state.selection!!;source.problem=null;picker.retry(denied);runCurrent();assertTrue(picker.state.loaded);assertNull(picker.state.problem)
        } finally {model.back();model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun pendingChannelConversationBusinessAndClosedEditorResponsesAreIsolated()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Inbox();val source=Source();val model=InboxViewModel(repo,source)
        try {
            model.load(101,60);runCurrent();model.open(901);runCurrent();val reply=model.reply;val picker=reply.quickReplies!!;val a=ReplyDraftContext(101,901,60)
            reply.open(a);var parent=reply.state.selection!!;reply.update("Private A",parent);source.hold=true;reply.openQuickReplies(parent);runCurrent()
            repo.channel="telegram";model.open(901);runCurrent();reply.open(a);source.pending[0].complete(page());runCurrent();assertEquals("telegram",picker.state.context?.channel);assertFalse(picker.state.loaded);assertEquals("Private A",reply.state.text)
            parent=reply.state.selection!!;reply.openQuickReplies(parent);runCurrent();model.open(902);runCurrent();reply.open(ReplyDraftContext(101,902,60));source.pending[1].complete(page(101,"telegram"));runCurrent();assertEquals("",reply.state.text);assertFalse(picker.state.loaded)
            repo.channel=null;model.open(901);runCurrent();reply.open(a);parent=reply.state.selection!!;assertEquals("Private A",reply.state.text);reply.openQuickReplies(parent);runCurrent()
            reply.close(parent);reply.open(a);source.pending[2].complete(page());runCurrent();assertFalse(picker.state.loaded);assertEquals("Private A",reply.state.text)
            parent=reply.state.selection!!;reply.openQuickReplies(parent);runCurrent();model.load(202,61);runCurrent();source.pending[3].complete(page());runCurrent();assertNull(picker.state.context);assertEquals("",reply.state.text)
            model.open(951);runCurrent();reply.open(ReplyDraftContext(202,951,61));source.hold=false;reply.openQuickReplies(reply.state.selection!!);runCurrent();assertEquals(listOf(9202),picker.choices.map {it.template.id})
        } finally {model.back();model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun unknownChannelAndStaleReloadedTemplateSnapshotsCannotInsert()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val repo=Inbox();val source=Source();val model=InboxViewModel(repo,source)
        try {
            model.load(101,60);runCurrent();repo.channel="email";model.open(901);runCurrent();val reply=model.reply;val picker=reply.quickReplies!!;val a=ReplyDraftContext(101,901,60);reply.open(a);reply.openQuickReplies(reply.state.selection!!);runCurrent();assertNull(picker.state.context);assertTrue(source.requests.isEmpty())
            repo.channel="website";model.open(901);runCurrent();reply.open(a);val parent=reply.state.selection!!;reply.update("Own",parent);reply.openQuickReplies(parent);runCurrent();val token=picker.state.selection!!;val old=picker.choices[0]
            source.hold=true;picker.retry(token);runCurrent();assertFalse(reply.insert(old,parent));val updated=page().copy(items=page().items.mapIndexed {index,row->if(index==0)row.copy(text="Updated {{client}}") else row});source.pending[0].complete(updated);runCurrent()
            assertFalse(reply.insert(old,parent));assertEquals("Own",reply.state.text);assertTrue(reply.insert(picker.choices[0],parent));assertEquals("Own\nUpdated {{client}}",reply.state.text)
        } finally {model.back();model.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sharedRawUnicodeFiltersRevokeOnlyChangedChoicesWithoutChangingLoadedRowsOrLiteralInsertion() {
        val cases=JSONObject(fixture("quick-reply-raw-unicode-cases")).getJSONArray("cases")
        for(i in 0 until cases.length()){val row=cases.getJSONObject(i);val context=QuickReplyContext(draft().state.selection!!,"website");val session=QuickReplySession();session.bind(context);val request=session.open(context)!!;val owner=session.state.selection!!;session.search(row.getString("before"),owner);session.accept(JsonContracts.quickReplies(row.getString("page_json")),request);val old=session.choices.single();session.search(row.getString("after"),owner);val current=session.choices.single();val changed=row.getBoolean("changed");assertEquals(row.getString("after"),session.state.query);assertEquals(changed,current.filterRevision!=old.filterRevision);assertEquals(changed,session.resolve(old)==null);assertEquals(old.template.id,current.template.id);assertEquals(row.getString("template"),session.resolve(current));assertEquals(row.getString("inserted"),QuickReplyInsertion.text(row.getString("draft"),current.template.text));assertFalse(session.state.partial);session.close(owner);assertNull(session.resolve(current));assertEquals(row.getString("after"),session.state.query)}
    }
}
