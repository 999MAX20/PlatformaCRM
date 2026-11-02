package kz.zani.mobile.core

import org.json.JSONObject

data class SyntheticInboxReplyGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean,val keys:List<String>) {
    fun authorization(c:ReplyDraftContext):SyntheticInboxReplyAuthorization?=if(c.valid && c.business==business && c.conversation==conversation && actor>0 && update && keys.isNotEmpty() && keys.all {it.isNotEmpty() && it==SourceTextTrim.pythonStrip(it)} && keys.distinct().size==keys.size)SyntheticInboxReplyAuthorization(c,actor,keys.toList()) else null
}
data class SyntheticInboxReplyAuthorization internal constructor(val context:ReplyDraftContext,val actor:Int,val keys:List<String>)
data class InboxReplyAttempt(val localID:Int,val authorization:SyntheticInboxReplyAuthorization,val review:ReplyDraftReview,val key:String) {
    val path get()="/api/mobile/v1/inbox/${authorization.context.conversation}/reply/"
    val preparedHeaders get()=mapOf("Idempotency-Key" to key)
    // Immutable local snapshot of the same existing two-field request body.
    private val bodySnapshot=JSONObject().put("business",authorization.context.business).put("text",review.text).toString()
    fun preparedBody():String=bodySnapshot
}
sealed interface SyntheticInboxReplyOutcome {data class Response(val status:Int,val body:String):SyntheticInboxReplyOutcome;data object RejectedWithoutWrite:SyntheticInboxReplyOutcome;data object Unknown:SyntheticInboxReplyOutcome}
interface SyntheticInboxReplyPort {val grants:List<SyntheticInboxReplyGrant>;suspend fun execute(attempt:InboxReplyAttempt):SyntheticInboxReplyOutcome}
enum class InboxReplyPhase {PENDING,CONFIRMED,REJECTED,UNKNOWN}
enum class InboxReplyDelivery(val wire:String) {QUEUED("queued"),SENT("sent"),FAILED("failed")}
data class InboxReplyReceipt(val conversation:Int,val message:Int,val text:String,val delivery:InboxReplyDelivery,val createdAt:String,val sentAt:String?,val replayed:Boolean) {
    companion object {fun decode(body:String):InboxReplyReceipt?=runCatching {
        val root=JSONObject(body);val ok=root.get("ok");val replayed=root.get("replayed");require(ok is Boolean && ok && replayed is Boolean)
        val c=root.getJSONObject("conversation");val m=root.getJSONObject("message")
        fun integer(o:JSONObject,key:String):Int {val v=o.get(key);require(v is Int || v is Long);val n=(v as Number).toLong();require(n in 1L..Int.MAX_VALUE.toLong());return n.toInt()}
        fun text(key:String):String {val v=m.get(key);require(v is String);return v}
        val conversation=integer(c,"id");require(integer(m,"conversation_id")==conversation);val message=integer(m,"id");require(text("direction")=="outbound" && text("sender_type")=="manager")
        val value=text("text");val delivery=InboxReplyDelivery.entries.single {it.wire==text("status")};val created=text("created_at");require(TaskSnoozeValue.parse(created)!=null && m.has("sent_at"))
        val sent=if(m.isNull("sent_at"))null else text("sent_at").also {require(TaskSnoozeValue.parse(it)!=null)};require((delivery==InboxReplyDelivery.SENT)==(sent!=null))
        InboxReplyReceipt(conversation,message,value,delivery,created,sent,replayed as Boolean)
    }.getOrNull()}
    fun matches(a:InboxReplyAttempt)=conversation==a.authorization.context.conversation && a.review.text.codePointCount(0,a.review.text.length)<=500 && !text.codePoints().anyMatch {it in 0xD800..0xDFFF} && text==a.review.text
}
data class InboxReplyRecord(val attempt:InboxReplyAttempt,val phase:InboxReplyPhase,val receipt:InboxReplyReceipt?=null)
class InboxReplyLedger {
    var records:List<InboxReplyRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>();private val usedKeys=mutableMapOf<Pair<Int,Int>,MutableSet<String>>()
    private fun owner(c:ReplyDraftContext)=c.business to c.conversation
    private fun namespace(a:SyntheticInboxReplyAuthorization)=a.context.business to a.actor
    private fun nextKey(a:SyntheticInboxReplyAuthorization)=a.keys.firstOrNull {it !in usedKeys[namespace(a)].orEmpty()}
    fun blocked(c:ReplyDraftContext)=active.containsKey(owner(c))
    fun visible(a:SyntheticInboxReplyAuthorization?):InboxReplyRecord? {if(a==null)return null;return active[owner(a.context)]?.let {records[it]}?.takeIf {it.attempt.authorization==a}}
    fun canBegin(a:SyntheticInboxReplyAuthorization?)=a!=null && !blocked(a.context) && nextKey(a)!=null
    fun begin(review:ReplyDraftReview,a:SyntheticInboxReplyAuthorization):InboxReplyAttempt? {
        if(review.selection.context!=a.context || review.selection.generation<=0 || review.text.isEmpty() || review.text!=ReplyDraftText.stripped(review.raw) || !canBegin(a))return null
        val key=nextKey(a) ?: return null;val attempt=InboxReplyAttempt(records.size+1,a,review,key);usedKeys.getOrPut(namespace(a)){mutableSetOf()}.add(key);active[owner(a.context)]=records.size;records=records+InboxReplyRecord(attempt,InboxReplyPhase.PENDING);return attempt
    }
    fun complete(attempt:InboxReplyAttempt,outcome:SyntheticInboxReplyOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=InboxReplyPhase.PENDING)return
        var phase=InboxReplyPhase.UNKNOWN;var receipt:InboxReplyReceipt?=null
        when(outcome) {SyntheticInboxReplyOutcome.Unknown->Unit;SyntheticInboxReplyOutcome.RejectedWithoutWrite->phase=InboxReplyPhase.REJECTED
            is SyntheticInboxReplyOutcome.Response->{val r=InboxReplyReceipt.decode(outcome.body);if(outcome.status==200 && r!=null && r.matches(attempt)){phase=InboxReplyPhase.CONFIRMED;receipt=r}}}
        records=records.mapIndexed {n,r->if(n==i)r.copy(phase=phase,receipt=receipt) else r}
    }
    fun acknowledge(a:SyntheticInboxReplyAuthorization):Boolean {val r=visible(a) ?: return false;if(r.phase!=InboxReplyPhase.CONFIRMED && r.phase!=InboxReplyPhase.REJECTED)return false;active.remove(owner(a.context));return true}
}
