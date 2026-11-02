package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Source projection only, not the link command/picker/authority.
typealias InboxExistingLeadSource = InboxLinkLeadSource
data class SyntheticInboxExistingLeadGrant(val business:Int,val conversation:Int,val actor:Int,val leadsCreate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && leadsCreate && conversationsUpdate)SyntheticInboxExistingLeadAuthorization.create(c,actor)else null
}
data class SyntheticInboxExistingLeadAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxExistingLeadAuthorization(c,actor)}}
data class InboxExistingLeadReview(val source:InboxExistingLeadSource,val authorization:SyntheticInboxExistingLeadAuthorization,val visit:Int) {val valid get()=source.valid && source.lead?.let {it>0}==true && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxExistingLeadAttempt internal constructor(val localID:Int,val review:InboxExistingLeadReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/create-lead/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
// Generic LeadSerializer only. Required Lead.client must not be equated with conversation.client.
data class InboxExistingLeadReceipt private constructor(val id:Int,val business:Int,val client:Int,val message:String,val updatedAt:String) {
    companion object {fun decode(body:String,a:InboxExistingLeadAttempt):InboxExistingLeadReceipt?=runCatching {
        require(a.review.valid);val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject);val id=a.review.source.lead!!;require(directoryReadInteger(row.get("id"))==id.toLong() && directoryReadInteger(row.get("business"))==a.review.source.context.business.toLong());val client=directoryReadInteger(row.get("client"));val message=row.get("message");val updated=row.get("updated_at");require(client!=null && client>0 && client<=Int.MAX_VALUE && message is String && updated is String && updated.isNotEmpty());InboxExistingLeadReceipt(id,a.review.source.context.business,client.toInt(),message,updated)
    }.getOrNull()}
}
sealed interface SyntheticInboxExistingLeadOutcome {data class Response(val status:Int,val body:String):SyntheticInboxExistingLeadOutcome;data object RejectedWithoutWrite:SyntheticInboxExistingLeadOutcome;data object Unknown:SyntheticInboxExistingLeadOutcome}
interface SyntheticInboxExistingLeadPort {val grants:List<SyntheticInboxExistingLeadGrant>;suspend fun execute(a:InboxExistingLeadAttempt):SyntheticInboxExistingLeadOutcome}
enum class InboxExistingLeadPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxExistingLeadRecord(val attempt:InboxExistingLeadAttempt,val phase:InboxExistingLeadPhase,val result:InboxExistingLeadReceipt?=null)
class InboxExistingLeadLedger {
    private val history=mutableListOf<InboxExistingLeadRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxExistingLeadAuthorization?):InboxExistingLeadRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxExistingLeadReview):InboxExistingLeadAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxExistingLeadAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxExistingLeadRecord(a,InboxExistingLeadPhase.PENDING));return a}
    fun complete(a:InboxExistingLeadAttempt,outcome:SyntheticInboxExistingLeadOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxExistingLeadPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxExistingLeadOutcome.Unknown->history[i].copy(phase=InboxExistingLeadPhase.UNKNOWN);SyntheticInboxExistingLeadOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxExistingLeadPhase.REJECTED);is SyntheticInboxExistingLeadOutcome.Response->{val r=if(outcome.status==200)InboxExistingLeadReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxExistingLeadPhase.UNKNOWN else InboxExistingLeadPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxExistingLeadAuthorization,record:InboxExistingLeadRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxExistingLeadPhase.RESPONSE,InboxExistingLeadPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
