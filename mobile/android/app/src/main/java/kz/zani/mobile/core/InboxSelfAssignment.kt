package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxSelfAssignmentSource private constructor(val context:InboxConversationFilesContext,val assignedTo:Int?,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty() && (assignedTo==null || assignedTo>0)
    companion object {
        fun decode(body:String,c:InboxConversationFilesContext):InboxSelfAssignmentSource?=runCatching {
            val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid)
            require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong())
            val value=row.get("assigned_to");val id:Int?=if(value==JSONObject.NULL)null else {val raw=directoryReadInteger(value) ?: error("assigned_to");require(raw in 1..Int.MAX_VALUE.toLong());raw.toInt()}
            val updated=row.get("updated_at");require(updated is String && updated.isNotEmpty());InboxSelfAssignmentSource(c,id,updated)
        }.getOrNull()
    }
}
data class SyntheticInboxSelfAssignmentGrant(val business:Int,val conversation:Int,val actor:Int,val manage:Boolean,val activeMember:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && manage && activeMember)SyntheticInboxSelfAssignmentAuthorization.create(c,actor)else null
}
data class SyntheticInboxSelfAssignmentAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxSelfAssignmentAuthorization(c,actor)}}
data class InboxSelfAssignmentReview(val source:InboxSelfAssignmentSource,val authorization:SyntheticInboxSelfAssignmentAuthorization,val visit:Int) {val valid get()=source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxSelfAssignmentAttempt internal constructor(val localID:Int,val review:InboxSelfAssignmentReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/assign/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
data class InboxSelfAssignmentReceipt private constructor(val source:InboxSelfAssignmentSource) {companion object {fun decode(body:String,a:InboxSelfAssignmentAttempt):InboxSelfAssignmentReceipt? {if(!a.review.valid)return null;val s=InboxSelfAssignmentSource.decode(body,a.review.source.context) ?: return null;return if(s.assignedTo==a.review.authorization.actor)InboxSelfAssignmentReceipt(s)else null}}}
sealed interface SyntheticInboxSelfAssignmentOutcome {data class Response(val status:Int,val body:String):SyntheticInboxSelfAssignmentOutcome;data object RejectedWithoutWrite:SyntheticInboxSelfAssignmentOutcome;data object Unknown:SyntheticInboxSelfAssignmentOutcome}
interface SyntheticInboxSelfAssignmentPort {val grants:List<SyntheticInboxSelfAssignmentGrant>;suspend fun execute(a:InboxSelfAssignmentAttempt):SyntheticInboxSelfAssignmentOutcome}
enum class InboxSelfAssignmentPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxSelfAssignmentRecord(val attempt:InboxSelfAssignmentAttempt,val phase:InboxSelfAssignmentPhase,val result:InboxSelfAssignmentReceipt?=null)
class InboxSelfAssignmentLedger {
    private val history=mutableListOf<InboxSelfAssignmentRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxSelfAssignmentAuthorization?):InboxSelfAssignmentRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxSelfAssignmentReview):InboxSelfAssignmentAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxSelfAssignmentAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxSelfAssignmentRecord(a,InboxSelfAssignmentPhase.PENDING));return a}
    fun complete(a:InboxSelfAssignmentAttempt,outcome:SyntheticInboxSelfAssignmentOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxSelfAssignmentPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxSelfAssignmentOutcome.Unknown->history[i].copy(phase=InboxSelfAssignmentPhase.UNKNOWN);SyntheticInboxSelfAssignmentOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxSelfAssignmentPhase.REJECTED);is SyntheticInboxSelfAssignmentOutcome.Response->{val r=if(outcome.status==200)InboxSelfAssignmentReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxSelfAssignmentPhase.UNKNOWN else InboxSelfAssignmentPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxSelfAssignmentAuthorization,record:InboxSelfAssignmentRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxSelfAssignmentPhase.RESPONSE,InboxSelfAssignmentPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
