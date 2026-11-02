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
class InboxReplyReceiptTest {
    private val ctx=ReplyDraftContext(101,901,270)
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun fixturePort()=FixtureInboxReplyPort(fixture("inbox-reply-outcome"))
    private fun thread(b:Int=101,id:Int=901)=JsonContracts.thread(fixture("inbox-$b-$id"))
    private fun review(raw:String,c:ReplyDraftContext=ctx):ReplyDraftReview {val s=ReplyDraftSession();s.bind(c,true);s.open(c);s.update(raw,s.state.selection!!);s.prepare(s.state.selection!!);return s.state.review!!}
    private fun prepare(m:ReplyDraftModel,raw:String=" Reply ",epoch:Int=270) {m.verified(thread(),101,901,epoch);m.open(m.entryControl);m.update(raw,m.inputControl);m.prepare(m.control)}
    private class Controlled(override val grants:List<SyntheticInboxReplyGrant>):SyntheticInboxReplyPort {
        val calls=mutableListOf<InboxReplyAttempt>();val pending=mutableListOf<CompletableDeferred<SyntheticInboxReplyOutcome>>()
        override suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome {calls+=attempt;return CompletableDeferred<SyntheticInboxReplyOutcome>().also {pending+=it}.await()}
    }
    @Test fun sharedStrictReceiptCasesRetainRawKeyAndTerminalState() {
        val port=fixturePort();val grant=port.grants.first {it.business==101 && it.conversation==901};val a=grant.authorization(ctx)!!;val rows=JSONObject(fixture("inbox-reply-outcome")).getJSONArray("validation_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val ledger=InboxReplyLedger();val r=review(row.getString("raw"));val attempt=ledger.begin(r,a)!!;assertNull(ledger.begin(r,a));assertEquals("/api/mobile/v1/inbox/901/reply/",attempt.path);assertEquals(mapOf("Idempotency-Key" to grant.keys[0]),attempt.preparedHeaders)
            val body=JSONObject(attempt.preparedBody());assertEquals(setOf("business","text"),body.keys().asSequence().toSet());assertEquals(101,body.getInt("business"));assertEquals(r.text,body.getString("text"))
            ledger.complete(attempt,SyntheticInboxReplyOutcome.Response(row.getInt("status"),row.getJSONObject("response").toString()));val record=ledger.visible(a)!!;val yes=row.getString("expected")=="confirmed";assertEquals(row.getString("name"),if(yes)InboxReplyPhase.CONFIRMED else InboxReplyPhase.UNKNOWN,record.phase);assertEquals(r,record.attempt.review);assertEquals(attempt.key,record.attempt.key)
            ledger.complete(attempt,SyntheticInboxReplyOutcome.RejectedWithoutWrite);assertEquals(record,ledger.visible(a));assertEquals(yes,ledger.acknowledge(a));if(!yes){val newer=ctx.copy(epoch=271);assertTrue(ledger.blocked(newer));assertNull(ledger.visible(grant.authorization(newer)))}}
    }
    @Test fun getAndMalformedFakeGrantsCannotProvideUpdateOrConfiguredKeys() {
        for(g in listOf(SyntheticInboxReplyGrant(101,901,9001,false,listOf("k")),SyntheticInboxReplyGrant(101,901,0,true,listOf("k")),SyntheticInboxReplyGrant(202,901,9001,true,listOf("k")),SyntheticInboxReplyGrant(101,901,9001,true,emptyList()),SyntheticInboxReplyGrant(101,901,9001,true,listOf(" ")),SyntheticInboxReplyGrant(101,901,9001,true,listOf("k","k"))))assertNull(g.authorization(ctx))
        val m=ReplyDraftModel();prepare(m);assertFalse(m.canSubmit);assertFalse(m.hasTestPort)
        val denied=ReplyDraftModel(port=Controlled(listOf(SyntheticInboxReplyGrant(101,901,9001,false,listOf("k")))));prepare(denied);assertFalse(denied.canSubmit)
    }
    @Test fun opaqueKeysAreExactConsumedAcrossConversationsAndNeverGeneratedOnExhaustion() {
        val g=SyntheticInboxReplyGrant(101,901,9001,true,listOf("e\u0301","é"));val a=g.authorization(ctx)!!;val ledger=InboxReplyLedger();val first=ledger.begin(review("Reply"),a)!!;ledger.complete(first,SyntheticInboxReplyOutcome.RejectedWithoutWrite);assertTrue(ledger.acknowledge(a));val second=ledger.begin(review("Reply"),a)!!;assertEquals(g.keys[0],first.key);assertEquals(g.keys[1],second.key);assertNotEquals(first.key,second.key)
        ledger.complete(second,SyntheticInboxReplyOutcome.RejectedWithoutWrite);assertTrue(ledger.acknowledge(a));assertFalse(ledger.canBegin(a));assertNull(ledger.begin(review("Reply"),a));val cross=g.copy(conversation=902,keys=listOf(first.key)).authorization(ctx.copy(conversation=902))!!;assertFalse(ledger.canBegin(cross))
    }
    @Test fun staleRawReviewAndCapturedVisitCannotSubmitCurrentReview()=runTest {
        val p=Controlled(fixturePort().grants);val m=ReplyDraftModel(port=p);prepare(m," e\u0301 ");val old=m.state.review!!;val captured=m.control;m.back(m.returnControl);m.update(" é ",m.inputControl);m.prepare(m.control);val current=m.state.review!!;m.submit(old,m.control);m.submit(current,captured);assertTrue(p.calls.isEmpty());assertEquals(" é ",m.state.text)
    }
    @Test fun pendingDoubleClickClearAndReopenedEditorCannotReplaceAttempt()=runTest {
        val p=Controlled(fixturePort().grants);val m=ReplyDraftModel(port=p);prepare(m);val r=m.state.review!!;val c=m.control;val send=launch {m.submit(r,c)};runCurrent();val pending=m.submission!!;m.update("lost",m.inputControl);m.askClear(m.control);m.discard(m.state.selection!!);m.acknowledge(m.control,pending);m.submit(r,m.control);assertEquals(1,p.calls.size);assertEquals(r.raw,m.state.text);assertEquals(pending,m.submission);assertNull(m.clearConfirmation);m.back(m.returnControl);m.open(m.entryControl);assertEquals(pending,m.submission);assertNull(m.inputControl);p.pending[0].complete(SyntheticInboxReplyOutcome.Unknown);send.join()
    }
    @Test fun cancellationIsUnknownAndRereadEpochOrAcknowledgeCannotRecoverIt()=runTest {
        val p=Controlled(fixturePort().grants);val m=ReplyDraftModel(port=p);prepare(m);val r=m.state.review!!;val job=launch {m.submit(r,m.control)};runCurrent();job.cancelAndJoin();val unknown=m.submission!!;assertEquals(InboxReplyPhase.UNKNOWN,unknown.phase);m.acknowledge(m.control,unknown);m.verified(thread(),101,901,271);m.open(m.entryControl);assertTrue(m.submissionBlocked);assertNull(m.submission);assertNull(m.inputControl);assertEquals(r,unknown.attempt.review);assertEquals(1,p.calls.size)
    }
    @Test fun typedNoWriteRequiresFreshReviewAndUsesNextConfiguredKeyWithoutLosingRaw()=runTest {
        val p=Controlled(fixturePort().grants);val m=ReplyDraftModel(port=p);prepare(m);val r=m.state.review!!;val captured=m.control;val job=launch {m.submit(r,captured)};runCurrent();p.pending[0].complete(SyntheticInboxReplyOutcome.RejectedWithoutWrite);job.join();val rejected=m.submission!!;m.acknowledge(m.control,rejected);m.submit(r,captured);assertEquals(ReplyDraftPhase.EDITING,m.state.phase);assertNull(m.state.review);assertEquals(r.raw,m.state.text);assertEquals(1,p.calls.size)
        m.prepare(m.control);val next=launch {m.submit(m.state.review!!,m.control)};runCurrent();assertEquals(2,p.calls.size);assertNotEquals(p.calls[0].key,p.calls[1].key);assertEquals(p.calls[0].review,p.calls[1].review);p.pending[1].complete(SyntheticInboxReplyOutcome.Unknown);next.join()
    }
    @Test fun createdQueuedSentAndFailedAreReceiptsWithoutRecipientDeliveryProof()=runTest {
        val p=fixturePort()
        for((id,delivery) in listOf(901 to InboxReplyDelivery.QUEUED,911 to InboxReplyDelivery.SENT,931 to InboxReplyDelivery.FAILED)) {val c=ctx.copy(conversation=id);val a=p.grants.first {it.conversation==id}.authorization(c)!!;val ledger=InboxReplyLedger();val attempt=ledger.begin(review(" Reply ",c),a)!!;ledger.complete(attempt,p.execute(attempt));val record=ledger.visible(a)!!;assertEquals(InboxReplyPhase.CONFIRMED,record.phase);assertEquals(delivery,record.receipt!!.delivery);assertEquals(" Reply ",record.attempt.review.raw)}
    }
    @Test fun fakeReceiptDoesNotMutateThreadMessagesListUnreadOrIssueRereads()=runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler));val requests=mutableListOf<ReadRequest>();val repo=APIReadRepository(ReadTransport {q->requests+=q;ReadResponse(200,fixture(if(q.path.endsWith("/inbox/"))"inbox-101" else "inbox-101-901"))});val m=InboxViewModel(repo,replySubmission=fixturePort())
        try {m.load(101,272);runCurrent();m.open(901,m.control);runCurrent();val source=m.state.thread!!;val rows=m.state.items;val reads=requests.size;val v=m.reply;m.openReply(v.state.context!!,m.control);v.update(" Local test reply ",v.inputControl);v.prepare(v.control);val r=v.state.review!!;v.submit(r,v.control);val accepted=v.submission!!;assertEquals(InboxReplyPhase.CONFIRMED,accepted.phase);assertEquals(InboxReplyDelivery.QUEUED,accepted.receipt!!.delivery);assertEquals(source,m.state.thread);assertEquals(rows,m.state.items);assertEquals(reads,requests.size);v.acknowledge(v.control,accepted);assertNull(v.state.selection);assertEquals("",v.state.text);assertEquals(r,accepted.attempt.review);assertEquals(1,v.retainedAttemptCount)} finally {m.back();m.viewModelScope.cancel();Dispatchers.resetMain()}
    }
    @Test fun fiveHundredScalarExcerptCannotProveWholeLongManualReply()=runTest {
        val m=ReplyDraftModel(port=fixturePort());val raw="e\u0301".repeat(250)+"Z";prepare(m,raw);val r=m.state.review!!;m.submit(r,m.control);assertEquals(501,r.text.codePointCount(0,r.text.length));assertEquals(InboxReplyPhase.UNKNOWN,m.submission!!.phase);assertEquals(raw,m.submission!!.attempt.review.raw);assertEquals(raw,m.state.text)
    }
    @Test fun lateForeignOwnerCompletionCannotTouchReplacementInputOrVisit()=runTest {
        val f=fixturePort();val p=Controlled(f.grants);val m=ReplyDraftModel(port=p);prepare(m);val job=launch {m.submit(m.state.review!!,m.control)};runCurrent();val a=p.calls[0];m.verified(thread(202,951),202,951,273);m.open(m.entryControl);m.update(" Other owner private raw ",m.inputControl);val c=m.control;val input=m.inputControl;p.pending[0].complete(f.execute(a));job.join();assertEquals(c,m.control);assertEquals(input,m.inputControl);assertEquals(" Other owner private raw ",m.state.text);assertNull(m.submission)
    }
    @Test fun arbitraryHttpFailureIsNeverTypedNoWriteAndUnknownSurvivesOwnerClear()=runTest {
        val f=fixturePort();val p=Controlled(f.grants);val m=ReplyDraftModel(port=p);prepare(m);val job=launch {m.submit(m.state.review!!,m.control)};runCurrent();val a=p.calls[0];val response=f.execute(a) as SyntheticInboxReplyOutcome.Response;p.pending[0].complete(response.copy(status=409));job.join();assertEquals(InboxReplyPhase.UNKNOWN,m.submission!!.phase);m.clear();prepare(m);assertTrue(m.submissionBlocked);assertFalse(m.canSubmit);assertEquals(a,m.submission!!.attempt);assertEquals(1,p.calls.size)
    }
    @Test fun preparedBodySnapshotIsImmutableAcrossRepeatedReadsAndUnknownLedgerTransitions() {
        val rows=JSONObject(fixture("quick-reply-raw-unicode-cases")).getJSONArray("cases");val auth=fixturePort().grants.first {it.business==101 && it.conversation==901}.authorization(ctx)!!
        for(i in 0 until rows.length()){val row=rows.getJSONObject(i);val r=review(row.getString("inserted"));val ledger=InboxReplyLedger();val attempt=ledger.begin(r,auth)!!;val body=attempt.preparedBody();val headers=attempt.preparedHeaders;val obj=JSONObject(body);assertEquals(setOf("business","text"),obj.keys().asSequence().toSet());assertEquals(101,obj.getInt("business"));assertEquals(r.text,obj.getString("text"));repeat(64){assertEquals(body,attempt.preparedBody())};val chars=body.toCharArray();chars[0]='!';assertEquals(body,attempt.preparedBody());ledger.complete(attempt,SyntheticInboxReplyOutcome.Unknown);val record=ledger.visible(auth)!!;assertEquals(InboxReplyPhase.UNKNOWN,record.phase);assertEquals(attempt,record.attempt);assertEquals(r,record.attempt.review);assertEquals(body,record.attempt.preparedBody());assertEquals(headers,record.attempt.preparedHeaders);assertFalse(ledger.acknowledge(auth));assertNull(ledger.begin(r,auth));assertTrue(ledger.blocked(ctx.copy(epoch=271)))}
    }
}
