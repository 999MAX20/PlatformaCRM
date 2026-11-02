package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
// Bounded close omits optional reason; source serializer does not expose close_reason.
data class InboxLifecycleSource private constructor(val context:InboxConversationFilesContext,val status:String,val botEnabled:Boolean,val handoffRequired:Boolean,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty()
    companion object {
        fun decode(body:String,c:InboxConversationFilesContext):InboxLifecycleSource?=runCatching {
            val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong())
            val status=row.get("status");val bot=row.get("bot_enabled");val handoff=row.get("handoff_required");val updated=row.get("updated_at");require(status is String && bot is Boolean && handoff is Boolean && updated is String && updated.isNotEmpty());InboxLifecycleSource(c,status,bot,handoff,updated)
        }.getOrNull()
    }
}
enum class InboxLifecycleAction(val wire:String) {CLOSE("close"),REOPEN("reopen")}
data class SyntheticInboxLifecycleGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && update)SyntheticInboxLifecycleAuthorization.create(c,actor)else null
}
data class SyntheticInboxLifecycleAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxLifecycleAuthorization(c,actor)}}
data class InboxLifecycleReview(val source:InboxLifecycleSource,val authorization:SyntheticInboxLifecycleAuthorization,val action:InboxLifecycleAction,val visit:Int) {val valid get()=source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxLifecycleAttempt internal constructor(val localID:Int,val review:InboxLifecycleReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/${review.action.wire}/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
data class InboxLifecycleReceipt private constructor(val source:InboxLifecycleSource) {companion object {fun decode(body:String,a:InboxLifecycleAttempt):InboxLifecycleReceipt? {if(!a.review.valid)return null;val s=InboxLifecycleSource.decode(body,a.review.source.context) ?: return null;return if((if(a.review.action==InboxLifecycleAction.CLOSE)s.status=="closed" && !s.botEnabled && !s.handoffRequired else s.status=="open"))InboxLifecycleReceipt(s)else null}}}
sealed interface SyntheticInboxLifecycleOutcome {data class Response(val status:Int,val body:String):SyntheticInboxLifecycleOutcome;data object RejectedWithoutWrite:SyntheticInboxLifecycleOutcome;data object Unknown:SyntheticInboxLifecycleOutcome}
interface SyntheticInboxLifecyclePort {val grants:List<SyntheticInboxLifecycleGrant>;suspend fun execute(a:InboxLifecycleAttempt):SyntheticInboxLifecycleOutcome}
enum class InboxLifecyclePhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxLifecycleRecord(val attempt:InboxLifecycleAttempt,val phase:InboxLifecyclePhase,val result:InboxLifecycleReceipt?=null)
class InboxLifecycleLedger {
    private val history=mutableListOf<InboxLifecycleRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxLifecycleAuthorization?):InboxLifecycleRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxLifecycleReview):InboxLifecycleAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxLifecycleAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxLifecycleRecord(a,InboxLifecyclePhase.PENDING));return a}
    fun complete(a:InboxLifecycleAttempt,outcome:SyntheticInboxLifecycleOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxLifecyclePhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxLifecycleOutcome.Unknown->history[i].copy(phase=InboxLifecyclePhase.UNKNOWN);SyntheticInboxLifecycleOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxLifecyclePhase.REJECTED);is SyntheticInboxLifecycleOutcome.Response->{val r=if(outcome.status==200)InboxLifecycleReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxLifecyclePhase.UNKNOWN else InboxLifecyclePhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxLifecycleAuthorization,record:InboxLifecycleRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxLifecyclePhase.RESPONSE,InboxLifecyclePhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
