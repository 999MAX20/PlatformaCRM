package kz.zani.mobile

import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import kz.zani.mobile.core.*
import kz.zani.mobile.data.*
import kz.zani.mobile.ui.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class QuickReplyControlsTest {
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun page()=JsonContracts.quickReplies(fixture("quick-replies-101-website"))
    private fun thread()=JsonContracts.thread(fixture("inbox-101-901"))
    private val context=ReplyDraftContext(101,901,80)
    private inner class Source:QuickReplyRepository {
        val calls=mutableListOf<Pair<Int,String>>();val pending=mutableListOf<CompletableDeferred<QuickReplyPage>>()
        override suspend fun quickReplies(business:Int,channel:String):QuickReplyPage {calls+=business to channel;return CompletableDeferred<QuickReplyPage>().also {pending+=it}.await()}
    }
    private fun reply(source:Source,scope:CoroutineScope)=ReplyDraftModel(source,scope).also {it.verified(thread(),101,901,80);it.open(context)}
    @Test fun duplicateOpenPendingRetryAndStaleComposerBackCannotRestartRead()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!;val editor=reply.control!!;val input=reply.inputControl!!
        reply.update("Own manual text",input);val parent=reply.returnControl;val entry=picker.entryControl!!
        reply.openQuickReplies(editor,entry);runCurrent();val pending=picker.control!!
        reply.openQuickReplies(editor,entry);picker.retry(expected=pending);runCurrent();reply.back(expected=parent);reply.update("hidden stale composer",input);reply.prepare(editor)
        assertEquals(1,source.calls.size);assertEquals(pending,picker.control);assertTrue(picker.state.loading);assertEquals("Own manual text",reply.state.text);assertEquals(ReplyDraftPhase.EDITING,reply.state.phase)
        source.pending[0].complete(page());runCurrent();assertTrue(picker.state.loaded)
    }
    @Test fun continuousSearchSurvivesReadAndOldWindowBackRetryReject()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!
        reply.openQuickReplies(reply.control,picker.entryControl);runCurrent();val pending=picker.control!!;val input=picker.inputControl!!
        picker.search(" APPOINTMENTS ",input);val typed=picker.control!!;picker.close(expected=pending)
        assertEquals(typed,picker.control);assertEquals(input,picker.inputControl);source.pending[0].complete(page());runCurrent();val current=picker.control
        picker.close(expected=typed);picker.retry(expected=pending);runCurrent()
        assertEquals(current,picker.control);assertEquals(input,picker.inputControl);assertEquals(" APPOINTMENTS ",picker.state.query);assertEquals(listOf(9102),picker.choices.map {it.template.id});assertEquals(1,source.calls.size)
    }
    @Test fun currentLiteralInsertionRejectsFilterWindowOldInputAndDoublePick()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!;val editor=reply.control!!;val input=reply.inputControl!!
        reply.update("  Own manual note  \n",input);reply.openQuickReplies(editor,picker.entryControl);runCurrent();source.pending[0].complete(page());runCurrent()
        val filter=picker.inputControl!!;val stale=picker.choices[0];val old=picker.control!!;picker.search("{{client}}",filter);picker.search("",filter);val current=picker.control!!;val choice=picker.choices[0]
        assertFalse(reply.insert(stale,editor,current));assertFalse(reply.insert(choice,editor,old));assertTrue(reply.insert(choice,editor,current));val inserted=reply.state.text
        assertEquals("  Own manual note\n${choice.template.text}",inserted);assertTrue(inserted.contains("{{client}}"));assertNull(picker.control);assertNotEquals(editor.selection,reply.control!!.selection)
        reply.update("old input",input);assertFalse(reply.insert(choice,editor,current));assertEquals(inserted,reply.state.text)
    }
    @Test fun lateDismissedReadCannotAdvanceReopenedWindowAndOldSearchCannotFilterIt()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!;val editor=reply.control!!;val entry=picker.entryControl!!
        reply.openQuickReplies(editor,entry);runCurrent();val leaving=picker.control!!;val oldInput=picker.inputControl!!;picker.close(expected=leaving)
        reply.openQuickReplies(editor,entry);runCurrent();assertEquals(1,source.calls.size)
        reply.openQuickReplies(editor,picker.entryControl);runCurrent();val current=picker.control;val input=picker.inputControl
        source.pending[0].complete(page());runCurrent();picker.search("old filter",oldInput)
        assertEquals(current,picker.control);assertEquals(input,picker.inputControl);assertTrue(picker.state.loading);assertEquals("",picker.state.query)
        source.pending[1].complete(page());runCurrent();assertEquals(listOf(9101,9102,9103),picker.choices.map {it.template.id})
    }
    @Test fun deniedRetryCancellationAndUnknownPartialKeepDraftAndPreciseEmptyState()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!
        reply.update("Own retained text",reply.inputControl);reply.openQuickReplies(reply.control,picker.entryControl);runCurrent();val input=picker.inputControl!!
        source.pending[0].completeExceptionally(ReadException(ReadProblem.DENIED));runCurrent();val denied=picker.control!!
        assertEquals(ReadProblem.DENIED,picker.state.problem);assertEquals("Own retained text",reply.state.text);assertFalse(picker.showsEmpty)
        picker.retry(expected=denied);runCurrent();val pending=picker.control;picker.retry(expected=denied);picker.retry(expected=pending);runCurrent();assertEquals(2,source.calls.size)
        picker.search("no matching template",input);source.pending[1].complete(page().copy(count=null,hasNext=false,metadataKnown=false));runCurrent()
        assertTrue(picker.state.partial);assertTrue(picker.choices.isEmpty());assertFalse(picker.showsEmpty);assertEquals(input,picker.inputControl)
        picker.retry(expected=picker.control);runCurrent();source.pending[2].completeExceptionally(CancellationException("synthetic cancellation"));runCurrent()
        assertFalse(picker.state.loading);assertFalse(picker.state.loaded);assertNull(picker.state.problem);assertFalse(picker.showsEmpty);assertEquals("Own retained text",reply.state.text)
    }
    @Test fun reviewRoundtripAndPickerReturnRejectOldParentBackWithoutLosingText()=runTest {
        val source=Source();val reply=reply(source,backgroundScope);val picker=reply.quickReplies!!;reply.update("Own text",reply.inputControl)
        val editing=reply.returnControl;reply.prepare(reply.control);val review=reply.returnControl;reply.back(expected=editing);assertEquals(review,reply.returnControl)
        reply.back(expected=review);reply.prepare(reply.control);val review2=reply.returnControl;reply.back(expected=review)
        assertEquals(review.editor!!.selection,review2.editor!!.selection);assertNotEquals(review,review2);assertEquals(review2,reply.returnControl)
        reply.back(expected=review2);val parent=reply.returnControl;reply.openQuickReplies(reply.control,picker.entryControl);runCurrent();reply.back(expected=parent);assertNotNull(picker.control)
        reply.back(expected=reply.returnControl);assertNull(picker.control);assertNotNull(reply.control);assertEquals("Own text",reply.state.text)
        source.pending[0].complete(page());runCurrent();assertNull(picker.control);assertFalse(picker.state.loaded)
    }
    @Test fun clearConsentIsExactAcrossNewTypingDialogReplacementAndEditorReopen()=runTest {
        val reply=reply(Source(),backgroundScope);val control=reply.control!!;val input=reply.inputControl!!;reply.update("Own original",input)
        reply.askClear(control);val question=reply.clearConfirmation!!;reply.update("New own text",input);reply.confirmClear(question);assertEquals("New own text",reply.state.text);assertNull(reply.clearConfirmation)
        reply.askClear(control);val old=reply.clearConfirmation!!;reply.dismissClear(old);reply.askClear(control);val current=reply.clearConfirmation!!
        reply.dismissClear(old);reply.confirmClear(old);assertEquals(current,reply.clearConfirmation);assertEquals("New own text",reply.state.text)
        val stale=ReplyDraftReturnControl(control,null,null);reply.back(expected=stale);assertEquals(current,reply.clearConfirmation);reply.back(expected=reply.returnControl);assertNull(reply.clearConfirmation);assertEquals(control,reply.control)
        reply.close(expected=reply.returnControl);reply.open(context);reply.confirmClear(current);assertEquals("New own text",reply.state.text)
        reply.askClear(reply.control);reply.confirmClear(reply.clearConfirmation!!);assertNull(reply.control);assertEquals("",reply.state.text);reply.open(context);assertEquals("",reply.state.text)
    }
    @Test fun actualInboxCompositionPreservesMessagesUnreadAndReadsThenRevokesOldOwner()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val source=Source();val reads=mutableListOf<ReadRequest>()
        val repo=APIReadRepository(ReadTransport {r->reads+=r;ReadResponse(200,fixture(if(r.path.endsWith("/901/"))"inbox-101-901" else "inbox-101"))})
        val inbox=InboxViewModel(repo,source)
        try {
            inbox.load(101,80);runCurrent();inbox.open(901);runCurrent();val thread=inbox.state.thread;val before=reads.toList();val reply=inbox.reply;val picker=reply.quickReplies!!
            reply.open(context);reply.update("  Own note  \n",reply.inputControl);val editor=reply.control!!;reply.openQuickReplies(editor,picker.entryControl);runCurrent();source.pending[0].complete(page());runCurrent()
            val choice=picker.choices[0];assertTrue(reply.insert(choice,editor,picker.control));assertEquals(thread,inbox.state.thread);assertEquals(before,reads);assertEquals(listOf(101 to "website"),source.calls)
            val old=reply.inputControl;reply.askClear(reply.control);val consent=reply.clearConfirmation!!;inbox.back();reply.confirmClear(consent);reply.update("old source",old)
            assertNull(reply.control);assertEquals("",reply.state.text);assertNull(picker.state.context);assertNull(inbox.state.thread)
        } finally {inbox.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun sharedUnicodeWindowAndLiteralComposerInsertionRetainUnknownAttemptAcrossRereadAndEpoch()=runTest {
        val cases=org.json.JSONObject(fixture("quick-reply-raw-unicode-cases")).getJSONArray("cases")
        for(i in 0 until cases.length()) {
            val row=cases.getJSONObject(i);val source=Source();val calls=mutableListOf<InboxReplyAttempt>();val pending=CompletableDeferred<SyntheticInboxReplyOutcome>();val fixturePort=FixtureInboxReplyPort(fixture("inbox-reply-outcome"));val port=object:SyntheticInboxReplyPort {override val grants=fixturePort.grants;override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome {calls+=attempt;return pending.await()}}
            val reply=ReplyDraftModel(source,this,port);reply.verified(thread(),101,901,80);reply.open(context);reply.update(row.getString("draft"),reply.inputControl);val editor=reply.control!!;val picker=reply.quickReplies!!;reply.openQuickReplies(editor,picker.entryControl);runCurrent();source.pending.single().complete(JsonContracts.quickReplies(row.getString("page_json")));runCurrent()
            val input=picker.inputControl!!;picker.search(row.getString("before"),input);val oldChoice=picker.choices.single();val oldWindow=picker.control!!;picker.search(row.getString("after"),input);val choice=picker.choices.single();val current=picker.control!!;val changed=row.getBoolean("changed");assertEquals(row.getString("after"),picker.state.query);assertEquals(input,picker.inputControl);assertEquals(changed,oldWindow!=current);assertEquals(changed,oldChoice.filterRevision!=choice.filterRevision)
            if(changed){assertFalse(reply.insert(oldChoice,editor,current));assertFalse(reply.insert(choice,editor,oldWindow))}else assertEquals(row.getString("template"),picker.resolve(oldChoice,oldWindow))
            assertTrue(reply.insert(choice,editor,current));assertEquals(row.getString("inserted"),reply.state.text);assertNull(picker.control);assertEquals(1,source.calls.size);reply.prepare(reply.control);val review=reply.state.review!!;val job=launch {reply.submit(review,reply.control)};runCurrent();val attempt=calls.single();val body=attempt.preparedBody();pending.complete(SyntheticInboxReplyOutcome.Unknown);job.join();assertEquals(InboxReplyPhase.UNKNOWN,reply.submission!!.phase);assertEquals(row.getString("inserted"),attempt.review.raw);assertEquals(body,reply.submission!!.attempt.preparedBody());reply.openQuickReplies(reply.control,picker.entryControl);runCurrent();assertNull(picker.control);reply.verified(thread(),101,901,80);reply.open(reply.entryControl);assertTrue(reply.submissionBlocked);reply.verified(thread(),101,901,81);reply.open(reply.entryControl);assertTrue(reply.submissionBlocked);assertNull(reply.submission);assertNull(reply.inputControl);assertEquals(1,reply.retainedAttemptCount);assertEquals(1,calls.size)
        }
    }
}
