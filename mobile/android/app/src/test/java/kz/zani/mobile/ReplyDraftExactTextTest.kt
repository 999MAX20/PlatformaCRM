package kz.zani.mobile

import kz.zani.mobile.core.*
import kz.zani.mobile.data.JsonContracts
import kz.zani.mobile.ui.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ReplyDraftExactTextTest {
    private val ctx=ReplyDraftContext(101,901,260)
    private fun fixture(name:String)=javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use {it.readText()}
    private fun catalog()=JSONObject(fixture("reply-draft-exact-text"))
    private fun session(raw:String):ReplyDraftSession {val s=ReplyDraftSession();s.bind(ctx,true);s.open(ctx);s.update(raw,s.state.selection!!);s.prepare(s.state.selection!!);return s}
    private fun model():ReplyDraftModel {val m=ReplyDraftModel();m.verified(JsonContracts.thread(fixture("inbox-101-901")),101,901,260);m.open(m.entryControl);return m}
    @Test fun sharedPythonOnlyNormalizationCapturesExactRawAndEntirePreview() {
        val rows=catalog().getJSONArray("cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val s=session(row.getString("raw"));val raw=row.getString("raw");val valid=row.getBoolean("valid");assertEquals(raw,s.state.text);assertEquals(valid,s.state.phase==ReplyDraftPhase.REVIEW)
            if(valid){val selection=s.state.selection!!;val review=s.state.review!!;assertEquals(raw,review.raw);assertEquals(row.getString("text"),review.text);assertEquals(row.getInt("codepoints"),review.text.codePointCount(0,review.text.length));s.update("late",selection);assertEquals(review,s.state.review);s.back(selection);assertEquals(raw,s.state.text);assertEquals(ReplyDraftPhase.EDITING,s.state.phase)}else {assertTrue(s.state.emptyError);assertNull(s.state.review)}}
    }
    @Test fun snapshotEqualityDistinguishesRawEvenWhenNormalizedPreviewIsTheSame() {
        val rows=catalog().getJSONArray("snapshot_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val a=session(row.getString("left")).state.review!!;val b=session(row.getString("right")).state.review!!;assertEquals(row.getBoolean("text_equal"),a.text==b.text);assertEquals(row.getBoolean("review_equal"),a==b)}
    }
    @Test fun changedCanonicalSpellingInvalidatesOldClearWithoutDiscardingNewRaw() {
        val rows=catalog().getJSONArray("snapshot_cases")
        for(i in 0 until rows.length()) {val row=rows.getJSONObject(i);val a=row.getString("left");val b=row.getString("right");if(a==b)continue;val m=model();val input=m.inputControl;m.update(a,input);m.askClear(m.control);val question=m.clearConfirmation!!;m.update(b,input);m.confirmClear(question);assertNull(m.clearConfirmation);assertNotNull(m.state.selection);assertEquals(b,m.state.text);m.prepare(m.control);assertEquals(b,m.state.review!!.raw);assertEquals(ReplyDraftText.stripped(b),m.state.review!!.text)}
    }
    @Test fun longManualTextIsNotTruncatedToCommandResponseExcerptBudget() {
        val m=model();val raw="e\u0301".repeat(250)+"Z";m.update(raw,m.inputControl);m.prepare(m.control);val review=m.state.review!!;assertEquals(501,review.text.codePointCount(0,review.text.length));assertEquals(raw,review.raw);m.back(m.returnControl);assertEquals(raw,m.state.text);assertNull(m.state.review);assertEquals(raw,review.raw)
    }
    @Test fun sameOwnerPauseAndOtherConversationKeepIsolatedFullRawBuffers() {
        val raw="🙂".repeat(501);val s=session(raw);val old=s.state.selection!!;s.back(old);s.pause();s.bind(ctx.copy(conversation=902),true);s.open(s.state.context!!);s.update("Other conversation",s.state.selection!!);s.pause();s.bind(ctx,true);s.open(ctx);s.update("old callback",old);assertEquals(raw,s.state.text);s.prepare(s.state.selection!!);assertEquals(raw,s.state.review!!.raw)
    }
    @Test fun oldEpochCallbacksCannotRestorePrivateInputOrRewriteImmutableReview() {
        val m=model();val raw=" e\u0301 ";m.update(raw,m.inputControl);m.prepare(m.control);val review=m.state.review!!;val old=m.control;val oldReturn=m.returnControl;m.verified(JsonContracts.thread(fixture("inbox-101-901")),101,901,261);m.update("old",ReplyDraftInputControl(old!!));m.close(oldReturn);assertEquals("",m.state.text);assertNull(m.state.selection);assertEquals(raw,review.raw);assertEquals("e\u0301",review.text)
    }
    @Test fun identicalPreviewAfterBackStillHasDistinctRawReviewSnapshot() {
        val m=model();m.update("  Reply  ",m.inputControl);m.prepare(m.control);val before=m.state.review!!;val staleInput=ReplyDraftInputControl(m.control!!);m.back(m.returnControl);m.update("Reply",m.inputControl);m.prepare(m.control);val current=m.state.review!!;m.update("late",staleInput);assertEquals(before.text,current.text);assertNotEquals(before,current);assertEquals("  Reply  ",before.raw);assertEquals("Reply",current.raw);assertEquals(current,m.state.review)
    }
}
