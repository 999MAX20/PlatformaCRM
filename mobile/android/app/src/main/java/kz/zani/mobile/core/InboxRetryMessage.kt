package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Generic read observation only; synthetic UPDATE comes from a separate injected grant.
data class InboxRetryMessageSource private constructor(val context:InboxMessageFilesContext,val direction:String,val senderType:String,val text:String,val status:String) {
    val valid get()=context.valid
    val eligible get()=valid && direction=="outbound" && senderType in listOf("client","bot","manager","ai") && status in listOf("received","queued","failed")
    companion object {
        fun decode(body:String,c:InboxMessageFilesContext):InboxRetryMessageSource?=runCatching {val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject);decode(row,c)}.getOrNull()
        internal fun decode(row:JSONObject,c:InboxMessageFilesContext):InboxRetryMessageSource?=runCatching {
            require(c.valid && directoryReadInteger(row.get("id"))==c.message.toLong() && directoryReadInteger(row.get("conversation"))==c.conversation.toLong())
            fun text(key:String):String {val v=row.get(key);require(v is String);return v}
            InboxRetryMessageSource(c,text("direction"),text("sender_type"),text("text"),text("status"))
        }.getOrNull()
    }
}
data class InboxRetryOwner(val business:Int,val conversation:Int,val epoch:Int) {val valid get()=business>0 && conversation>0 && epoch>0}
data class SyntheticInboxRetryGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean) {
    fun authorization(owner:InboxRetryOwner)=if(owner.valid && business==owner.business && conversation==owner.conversation && actor>0 && update)SyntheticInboxRetryAuthorization.create(owner,actor) else null
}
data class SyntheticInboxRetryAuthorization private constructor(val owner:InboxRetryOwner,val actor:Int) {companion object {internal fun create(owner:InboxRetryOwner,actor:Int)=SyntheticInboxRetryAuthorization(owner,actor)}}
data class InboxRetryReview(val source:InboxRetryMessageSource,val authorization:SyntheticInboxRetryAuthorization,val visit:Int) {val valid get()=source.eligible && visit>0 && authorization.owner.valid && authorization.actor>0 && source.context.business==authorization.owner.business && source.context.conversation==authorization.owner.conversation && source.context.epoch==authorization.owner.epoch}
data class InboxRetryAttempt internal constructor(val localID:Int,val review:InboxRetryReview) {
    private val body="{\"message_id\":${review.source.context.message}}"
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/retry-message/"
    val query:Map<String,String> get()=emptyMap()
    val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()=body
}
data class InboxRetryReceipt private constructor(val id:Int,val conversation:Int,val retryOf:Int,val status:String,val text:String,val senderType:String,val createdAt:String,val sentAt:InboxObservedText) {
    companion object {fun decode(body:String,s:InboxRetryMessageSource):InboxRetryReceipt?=runCatching {
        require(s.eligible);val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject)
        val id=directoryReadInteger(row.get("id"));require(id!=null && id in 1L..Int.MAX_VALUE.toLong() && id!=s.context.message.toLong() && directoryReadInteger(row.get("conversation"))==s.context.conversation.toLong() && row.get("direction")=="outbound")
        fun field(key:String):String {val v=row.get(key);require(v is String);return v}
        val sender=field("sender_type");val rawText=field("text");val status=field("status");val created=field("created_at");require(sender==s.senderType && rawText==s.text && status in listOf("queued","sent","failed") && created.isNotEmpty() && row.has("sent_at") && directoryReadInteger(row.getJSONObject("payload_json").get("retry_of_message_id"))==s.context.message.toLong())
        InboxRetryReceipt(id.toInt(),s.context.conversation,s.context.message,status,rawText,sender,created,InboxObservedText.decode(row,"sent_at"))
    }.getOrNull()}
}
sealed interface SyntheticInboxRetryOutcome {data class Response(val status:Int,val body:String):SyntheticInboxRetryOutcome;data object RejectedWithoutWrite:SyntheticInboxRetryOutcome;data object Unknown:SyntheticInboxRetryOutcome}
interface SyntheticInboxRetryPort {val grants:List<SyntheticInboxRetryGrant>;suspend fun execute(attempt:InboxRetryAttempt):SyntheticInboxRetryOutcome}
enum class InboxRetryPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxRetryRecord(val attempt:InboxRetryAttempt,val phase:InboxRetryPhase,val result:InboxRetryReceipt?=null)
class InboxRetryLedger {
    var records:List<InboxRetryRecord> = emptyList();private set
    private val active=mutableMapOf<Pair<Int,Int>,Int>()
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxRetryAuthorization?):InboxRetryRecord? {auth ?: return null;if(!auth.owner.valid || auth.actor<=0)return null;val i=active[auth.owner.business to auth.owner.conversation] ?: return null;return records[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxRetryReview):InboxRetryAttempt? {if(!review.valid || blocked(review.source.context.business,review.source.context.conversation))return null;val a=InboxRetryAttempt(records.size+1,review);active[review.source.context.business to review.source.context.conversation]=records.size;records=records+InboxRetryRecord(a,InboxRetryPhase.PENDING);return a}
    fun complete(attempt:InboxRetryAttempt,outcome:SyntheticInboxRetryOutcome) {
        val i=records.indexOfFirst {it.attempt==attempt};if(i<0 || records[i].phase!=InboxRetryPhase.PENDING)return
        val result=if(outcome is SyntheticInboxRetryOutcome.Response && outcome.status==201)InboxRetryReceipt.decode(outcome.body,attempt.review.source) else null
        val phase=when {outcome==SyntheticInboxRetryOutcome.RejectedWithoutWrite->InboxRetryPhase.REJECTED;result!=null->InboxRetryPhase.RESPONSE;else->InboxRetryPhase.UNKNOWN}
        records=records.mapIndexed {index,r->if(index==i)r.copy(phase=phase,result=result)else r}
    }
    fun acknowledge(auth:SyntheticInboxRetryAuthorization,record:InboxRetryRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxRetryPhase.RESPONSE,InboxRetryPhase.REJECTED))return false;active.remove(auth.owner.business to auth.owner.conversation);return true}
}
