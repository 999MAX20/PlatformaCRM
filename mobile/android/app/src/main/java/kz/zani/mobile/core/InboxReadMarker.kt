package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxReadMarkerSource private constructor(val context:InboxConversationFilesContext,val unreadCount:Long,val updatedAt:String) {
    val valid get()=context.valid && unreadCount>=0 && updatedAt.isNotEmpty()
    companion object {
        fun decode(body:String,c:InboxConversationFilesContext):InboxReadMarkerSource?=runCatching {
            val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid)
            require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong())
            val count=directoryReadInteger(row.get("unread_count"));val updated=row.get("updated_at");require(count!=null && count>=0 && updated is String && updated.isNotEmpty());InboxReadMarkerSource(c,count,updated)
        }.getOrNull()
    }
}
enum class InboxReadMarkerAction(val wire:String) {READ("mark-read"),UNREAD("mark-unread")}
data class SyntheticInboxReadMarkerGrant(val business:Int,val conversation:Int,val actor:Int,val update:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && update)SyntheticInboxReadMarkerAuthorization.create(c,actor)else null
}
data class SyntheticInboxReadMarkerAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxReadMarkerAuthorization(c,actor)}}
data class InboxReadMarkerReview(val source:InboxReadMarkerSource,val authorization:SyntheticInboxReadMarkerAuthorization,val action:InboxReadMarkerAction,val visit:Int) {val valid get()=source.valid && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxReadMarkerAttempt internal constructor(val localID:Int,val review:InboxReadMarkerReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/${review.action.wire}/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
data class InboxReadMarkerReceipt private constructor(val source:InboxReadMarkerSource) {companion object {fun decode(body:String,a:InboxReadMarkerAttempt):InboxReadMarkerReceipt? {if(!a.review.valid)return null;val s=InboxReadMarkerSource.decode(body,a.review.source.context) ?: return null;return if((if(a.review.action==InboxReadMarkerAction.READ)s.unreadCount==0L else s.unreadCount>=1L))InboxReadMarkerReceipt(s)else null}}}
sealed interface SyntheticInboxReadMarkerOutcome {data class Response(val status:Int,val body:String):SyntheticInboxReadMarkerOutcome;data object RejectedWithoutWrite:SyntheticInboxReadMarkerOutcome;data object Unknown:SyntheticInboxReadMarkerOutcome}
interface SyntheticInboxReadMarkerPort {val grants:List<SyntheticInboxReadMarkerGrant>;suspend fun execute(a:InboxReadMarkerAttempt):SyntheticInboxReadMarkerOutcome}
enum class InboxReadMarkerPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxReadMarkerRecord(val attempt:InboxReadMarkerAttempt,val phase:InboxReadMarkerPhase,val result:InboxReadMarkerReceipt?=null)
class InboxReadMarkerLedger {
    private val history=mutableListOf<InboxReadMarkerRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxReadMarkerAuthorization?):InboxReadMarkerRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxReadMarkerReview):InboxReadMarkerAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxReadMarkerAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxReadMarkerRecord(a,InboxReadMarkerPhase.PENDING));return a}
    fun complete(a:InboxReadMarkerAttempt,outcome:SyntheticInboxReadMarkerOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxReadMarkerPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxReadMarkerOutcome.Unknown->history[i].copy(phase=InboxReadMarkerPhase.UNKNOWN);SyntheticInboxReadMarkerOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxReadMarkerPhase.REJECTED);is SyntheticInboxReadMarkerOutcome.Response->{val r=if(outcome.status==200)InboxReadMarkerReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxReadMarkerPhase.UNKNOWN else InboxReadMarkerPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxReadMarkerAuthorization,record:InboxReadMarkerRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxReadMarkerPhase.RESPONSE,InboxReadMarkerPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
