package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxPrioritySource private constructor(val context:InboxConversationFilesContext,val priority:String,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty()
    companion object {
        fun decode(body:String,c:InboxConversationFilesContext):InboxPrioritySource?=runCatching {val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong());val priority=row.get("priority");val updated=row.get("updated_at");require(priority is String && updated is String && updated.isNotEmpty());InboxPrioritySource(c,priority,updated)}.getOrNull()
    }
}
enum class InboxPriorityValue(val wire:String) {LOW("low"),NORMAL("normal"),HIGH("high"),URGENT("urgent")}
data class SyntheticInboxPriorityGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && update)SyntheticInboxPriorityAuthorization.create(c,actor)else null
}
data class SyntheticInboxPriorityAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxPriorityAuthorization(c,actor)}}
data class InboxPriorityReview(val source:InboxPrioritySource,val authorization:SyntheticInboxPriorityAuthorization,val value:InboxPriorityValue,val visit:Int) {val valid get()=source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxPriorityAttempt internal constructor(val localID:Int,val review:InboxPriorityReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/set-priority/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{\"priority\":\"${review.value.wire}\"}"
}
data class InboxPriorityReceipt private constructor(val source:InboxPrioritySource) {companion object {fun decode(body:String,a:InboxPriorityAttempt):InboxPriorityReceipt? {if(!a.review.valid)return null;val s=InboxPrioritySource.decode(body,a.review.source.context) ?: return null;return if(s.priority==a.review.value.wire)InboxPriorityReceipt(s)else null}}}
sealed interface SyntheticInboxPriorityOutcome {data class Response(val status:Int,val body:String):SyntheticInboxPriorityOutcome;data object RejectedWithoutWrite:SyntheticInboxPriorityOutcome;data object Unknown:SyntheticInboxPriorityOutcome}
interface SyntheticInboxPriorityPort {val grants:List<SyntheticInboxPriorityGrant>;suspend fun execute(a:InboxPriorityAttempt):SyntheticInboxPriorityOutcome}
enum class InboxPriorityPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxPriorityRecord(val attempt:InboxPriorityAttempt,val phase:InboxPriorityPhase,val result:InboxPriorityReceipt?=null)
class InboxPriorityLedger {
    private val history=mutableListOf<InboxPriorityRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxPriorityAuthorization?):InboxPriorityRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxPriorityReview):InboxPriorityAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxPriorityAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxPriorityRecord(a,InboxPriorityPhase.PENDING));return a}
    fun complete(a:InboxPriorityAttempt,outcome:SyntheticInboxPriorityOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxPriorityPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxPriorityOutcome.Unknown->history[i].copy(phase=InboxPriorityPhase.UNKNOWN);SyntheticInboxPriorityOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxPriorityPhase.REJECTED);is SyntheticInboxPriorityOutcome.Response->{val r=if(outcome.status==200)InboxPriorityReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxPriorityPhase.UNKNOWN else InboxPriorityPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxPriorityAuthorization,record:InboxPriorityRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxPriorityPhase.RESPONSE,InboxPriorityPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
