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
class InboxHandoffTest {
    private val ctx=ReplyDraftContext(101,901,280)
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun thread(b:Int=101,id:Int=901)=JsonContracts.thread(fixture("inbox-$b-$id"))
    private fun fixturePort()=FixtureHandoffPort(fixture("inbox-handoff-outcome"))
    private fun review(raw:String):HandoffReview {val s=HandoffDraftSession();s.bind(ctx,true);s.open(ctx);s.update(raw,s.state.selection!!);s.prepare(s.state.selection!!);return s.state.review!!}
    private fun prepare(m:InboxHandoffModel,raw:String=" Manager review ",epoch:Int=280) {m.verified(thread(),101,901,epoch);m.open(m.entryControl);m.update(raw,m.inputControl);m.prepare(m.control)}
    private class Controlled(override val grants:List<SyntheticHandoffGrant>):SyntheticHandoffPort {
        val calls=mutableListOf<HandoffAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticHandoffOutcome>>()
        override suspend fun execute(attempt:HandoffAttempt):SyntheticHandoffOutcome {calls+=attempt;return CompletableDeferred<SyntheticHandoffOutcome>().also {pending+=it}.await()}
    }
    @Test fun prepareFeedbackUsesSharedReasonsThroughVisibleModelWithoutAttempt() {
        val rows=JSONObject(fixture("inbox-handoff-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {
            val row=rows.getJSONObject(i);val raw=row.getString("raw");val valid=row.getBoolean("valid")
            val p=Controlled(fixturePort().grants);val m=InboxHandoffModel(p)
            m.verified(thread(),101,901,280);m.open(m.entryControl);val stale=m.control
            m.back(m.returnControl);m.open(m.entryControl);m.update(raw,m.inputControl)
            val before=m.state;val current=m.control;val input=m.inputControl
            assertNotNull(current);assertNotNull(input);assertNotEquals(stale,current)
            m.prepare(null);m.prepare(stale)
            assertEquals(before,m.state);assertEquals(current,m.control);assertEquals(input,m.inputControl)
            m.prepare(current)
            assertEquals(row.getString("name"),!valid,m.state.inputError)
            assertEquals(raw,m.state.raw);assertNull(m.clearConfirmation)
            assertEquals(if(valid)ReplyDraftPhase.REVIEW else ReplyDraftPhase.EDITING,m.state.phase)
            assertEquals(valid,m.state.review!=null);assertEquals(0,m.retainedAttemptCount);assertNull(m.record);assertFalse(m.blocked);assertTrue(p.calls.isEmpty())
            if(valid) {
                assertEquals(raw,m.state.review!!.value.raw);assertEquals(row.getString("reason"),m.state.review!!.value.reason)
            } else {
                assertEquals(current,m.control);assertEquals(input,m.inputControl);assertFalse(m.canSubmit)
                m.update(" corrected ",input);assertFalse(m.state.inputError);assertEquals(" corrected ",m.state.raw)
                m.prepare(m.control);assertFalse(m.state.inputError);assertEquals("corrected",m.state.review!!.value.reason)
                assertEquals(" corrected ",m.state.review!!.value.raw);assertEquals(0,m.retainedAttemptCount);assertTrue(p.calls.isEmpty())
            }
        }
    }
    @Test fun sharedReasonsAllowExplicitBlankAndPreserveWholeExactRaw() {
        val rows=JSONObject(fixture("inbox-handoff-outcome")).getJSONArray("input_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=HandoffDraftSession();s.bind(ctx,true);s.open(ctx);val selection=s.state.selection!!;val raw=row.getString("raw");s.update(raw,selection);val valid=row.getBoolean("valid");assertEquals(valid,s.prepare(selection));assertEquals(raw,s.state.raw);if(valid){assertEquals(row.getString("reason"),s.state.review!!.value.reason);s.back(selection);assertEquals(raw,s.state.raw)}}
        assertNull(HandoffReason.make("A\uD800B"))
    }
    @Test fun exactReviewPairsDoNotCollapseCanonicalOrRawOnlyChanges() {
        val rows=JSONObject(fixture("inbox-handoff-outcome")).getJSONArray("review_pairs");for(i in 0 until rows.length()){val row=rows.getJSONObject(i);assertEquals(row.getBoolean("equal"),review(row.getString("left"))==review(row.getString("right")))}
    }
    @Test fun sharedStrictDirectReceiptsNeverInventReplyKeyOrVersion() {
        val a=SyntheticHandoffGrant(101,901,9001,true).authorization(ctx)!!;val rows=JSONObject(fixture("inbox-handoff-outcome")).getJSONArray("validation_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val ledger=HandoffLedger();val r=review(row.getString("raw"));val attempt=ledger.begin(r,a)!!;assertNull(ledger.begin(r,a));assertEquals("/api/inbox/conversations/901/handoff/",attempt.path);assertTrue(attempt.preparedHeaders.isEmpty());val body=JSONObject(attempt.preparedBody());assertEquals(setOf("reason"),body.keys().asSequence().toSet());assertEquals(r.value.reason,body.getString("reason"))
            ledger.complete(attempt,SyntheticHandoffOutcome.Response(row.getInt("status"),row.getString("response_json")));val yes=row.getString("expected")=="confirmed";val record=ledger.visible(a)!!;assertEquals(row.getString("name"),if(yes)HandoffPhase.CONFIRMED else HandoffPhase.UNKNOWN,record.phase);ledger.complete(attempt,SyntheticHandoffOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(a));assertEquals(yes,ledger.acknowledge(a));assertEquals(r,record.attempt.review);if(!yes){val newer=ctx.copy(epoch=281);assertTrue(ledger.blocked(newer));assertNull(ledger.visible(SyntheticHandoffGrant(101,901,9001,true).authorization(newer)))}}
    }
    @Test fun getDefaultAndDeniedForeignOrInvalidActorCannotGrantHandoff() {
        val m=InboxHandoffModel();prepare(m);assertNull(m.entryControl);assertNull(m.control);assertFalse(m.canSubmit)
        for(g in listOf(SyntheticHandoffGrant(101,901,9001,false),SyntheticHandoffGrant(202,901,9001,true),SyntheticHandoffGrant(101,901,0,true)))assertNull(g.authorization(ctx))
    }
    @Test fun rawCanonicalTypingInvalidatesOldResetAndCapturedReviewVisit()=runTest {
        val p=Controlled(fixturePort().grants);val m=InboxHandoffModel(p);m.verified(thread(),101,901,280);m.open(m.entryControl);m.update(" e\u0301 ",m.inputControl);m.askClear(m.control);val reset=m.clearConfirmation!!;m.update(" é ",m.inputControl);m.confirmClear(reset);assertEquals(" é ",m.state.raw);assertNotNull(m.control);assertNull(m.clearConfirmation);m.prepare(m.control);val old=m.state.review!!;val captured=m.control;m.back(m.returnControl);m.update(" e\u0301 ",m.inputControl);m.prepare(m.control);m.submit(old,m.control);m.submit(m.state.review!!,captured);assertTrue(p.calls.isEmpty())
    }
    @Test fun pendingCannotRepeatResetOrLoseRawThroughCloseAndReopen()=runTest {
        val p=Controlled(fixturePort().grants);val m=InboxHandoffModel(p);prepare(m);val r=m.state.review!!;val job=launch {m.submit(r,m.control)};runCurrent();val pending=m.record!!;m.update("lost",m.inputControl);m.askClear(m.control);m.prepare(m.control);m.acknowledge(m.control,pending);m.submit(r,m.control);assertEquals(1,p.calls.size);assertEquals(pending,m.record);assertEquals(r.value.raw,m.state.raw);assertNull(m.clearConfirmation);m.back(m.returnControl);m.open(m.entryControl);assertEquals(pending,m.record);assertNull(m.inputControl);p.pending[0].complete(SyntheticHandoffOutcome.Unknown);job.join()
    }
    @Test fun cancellationUnknownAndNewEpochCannotProveOrClearOutcome()=runTest {
        val p=Controlled(fixturePort().grants);val m=InboxHandoffModel(p);prepare(m);val r=m.state.review!!;val job=launch {m.submit(r,m.control)};runCurrent();job.cancelAndJoin();val record=m.record!!;assertEquals(HandoffPhase.UNKNOWN,record.phase);m.acknowledge(m.control,record);m.verified(thread(),101,901,281);m.open(m.entryControl);assertTrue(m.blocked);assertNull(m.record);assertNull(m.inputControl);assertEquals(r,record.attempt.review)
    }
    @Test fun typedNoWriteRequiresFreshBlankReasonReviewWithoutServerKey()=runTest {
        val p=Controlled(fixturePort().grants);val m=InboxHandoffModel(p);prepare(m," \n ");val r=m.state.review!!;val c=m.control;val job=launch {m.submit(r,c)};runCurrent();p.pending[0].complete(SyntheticHandoffOutcome.RejectedWithoutWrite);job.join();m.acknowledge(m.control,m.record!!);m.submit(r,c);assertEquals(1,p.calls.size);assertEquals(ReplyDraftPhase.EDITING,m.state.phase);assertEquals(r.value.raw,m.state.raw);assertNull(m.state.review);m.prepare(m.control);val next=launch {m.submit(m.state.review!!,m.control)};runCurrent();assertNotEquals(p.calls[0].localID,p.calls[1].localID);assertTrue(p.calls.all {it.preparedHeaders.isEmpty()});assertEquals(r.value,p.calls[1].review.value);p.pending[1].complete(SyntheticHandoffOutcome.Unknown);next.join()
    }
    @Test fun fakeReceiptLeavesThreadReadFlagMessagesRowsUnreadAndReadCountUntouched()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val reads=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {q->reads+=q;ReadResponse(200,fixture(if(q.path.endsWith("/inbox/"))"inbox-101" else "inbox-101-901"))});val m=InboxViewModel(repo,replySubmission=FixtureInboxReplyPort(fixture("inbox-reply-outcome")),handoffSubmission=fixturePort())
        try {m.load(101,282);runCurrent();m.open(901,m.control);runCurrent();val source=m.state.thread!!;val rows=m.state.items;val flag=m.handoffState;val before=reads.size;val parent=m.control;val returned=m.returnControl;m.openHandoff(m.handoff.entryControl,parent);m.openReply(m.reply.state.context!!,m.control);m.backToThreadList(returned);assertNotNull(m.handoff.control);assertNull(m.reply.control);assertEquals(source,m.state.thread);val h=m.handoff;h.update(" Saved test reason ",h.inputControl);h.prepare(h.control);h.submit(h.state.review!!,h.control);val record=h.record!!;assertEquals(HandoffPhase.CONFIRMED,record.phase);assertEquals(source,m.state.thread);assertEquals(rows,m.state.items);assertEquals(flag,m.handoffState);assertEquals(before,reads.size);h.acknowledge(h.control,record);assertNull(h.control);assertEquals("",h.state.raw);assertEquals(1,h.retainedAttemptCount)} finally {m.back();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun lateForeignOwnerResultDoesNotInvalidateReplacementInputOrVisit()=runTest {
        val f=fixturePort();val p=Controlled(f.grants);val m=InboxHandoffModel(p);prepare(m);val job=launch {m.submit(m.state.review!!,m.control)};runCurrent();val a=p.calls[0];m.verified(thread(202,951),202,951,283);m.open(m.entryControl);m.update(" Other owner ",m.inputControl);val c=m.control;val input=m.inputControl;p.pending[0].complete(f.execute(a));job.join();assertEquals(c,m.control);assertEquals(input,m.inputControl);assertEquals(" Other owner ",m.state.raw);assertNull(m.record)
    }
    @Test fun sameOwnerBuffersAreIsolatedAndEpochClearsOnlyOrdinaryVisibleReason() {
        val s=HandoffDraftSession();s.bind(ctx,true);s.open(ctx);s.update(" Own raw ",s.state.selection!!);s.pause();val other=ctx.copy(conversation=902);s.bind(other,true);s.open(other);s.update(" Other raw ",s.state.selection!!);s.pause();s.bind(ctx,true);s.open(ctx);assertEquals(" Own raw ",s.state.raw);s.bind(ctx.copy(epoch=281),true);assertEquals("",s.state.raw);assertNull(s.state.selection)
    }
    @Test fun longCompleteReasonHasNoReplyExcerptLimitAndRereadCannotClearUnknown()=runTest {
        val m=InboxHandoffModel(fixturePort());val raw="e\u0301".repeat(1000);prepare(m,raw);m.submit(m.state.review!!,m.control);assertEquals(HandoffPhase.CONFIRMED,m.record!!.phase);assertEquals(raw,m.record!!.receipt!!.reason)
        val p=Controlled(fixturePort().grants);val u=InboxHandoffModel(p);prepare(u);val job=launch {u.submit(u.state.review!!,u.control)};runCurrent();p.pending[0].complete(SyntheticHandoffOutcome.Unknown);job.join();val attempt=u.record!!.attempt;u.clear();prepare(u);assertTrue(u.blocked);assertFalse(u.canSubmit);assertEquals(attempt,u.record!!.attempt)
    }
}
