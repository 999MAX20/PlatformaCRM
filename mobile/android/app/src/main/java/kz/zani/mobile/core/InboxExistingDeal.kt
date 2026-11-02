package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Source projection only, not the link command/picker/authority.
typealias InboxExistingDealSource = InboxLinkDealSource
data class SyntheticInboxExistingDealGrant(val business:Int,val conversation:Int,val actor:Int,val dealsCreate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && dealsCreate && conversationsUpdate)SyntheticInboxExistingDealAuthorization.create(c,actor)else null
}
data class SyntheticInboxExistingDealAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxExistingDealAuthorization(c,actor)}}
data class InboxExistingDealReview(val source:InboxExistingDealSource,val authorization:SyntheticInboxExistingDealAuthorization,val visit:Int) {val valid get()=source.valid && source.deal?.let {it>0}==true && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxExistingDealAttempt internal constructor(val localID:Int,val review:InboxExistingDealReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/create-deal/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
// Generic DealSerializer identity/title/relations only; sensitive, actor and lifecycle data are not retained.
data class InboxExistingDealReceipt private constructor(val id:Int,val business:Int,val client:Int,val lead:Int?,val title:String,val updatedAt:String) {
    companion object {fun decode(body:String,a:InboxExistingDealAttempt):InboxExistingDealReceipt?=runCatching {
        require(a.review.valid);val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject);val id=a.review.source.deal!!;require(directoryReadInteger(row.get("id"))==id.toLong() && directoryReadInteger(row.get("business"))==a.review.source.context.business.toLong());val client=directoryReadInteger(row.get("client"));val title=row.get("title");val updated=row.get("updated_at");require(client!=null && client>0 && client<=Int.MAX_VALUE && title is String && updated is String && updated.isNotEmpty() && row.has("lead"));val lead=if(row.isNull("lead"))null else directoryReadInteger(row.get("lead"))!!.also {require(it>0 && it<=Int.MAX_VALUE)}.toInt();InboxExistingDealReceipt(id,a.review.source.context.business,client.toInt(),lead,title,updated)
    }.getOrNull()}
}
sealed interface SyntheticInboxExistingDealOutcome {data class Response(val status:Int,val body:String):SyntheticInboxExistingDealOutcome;data object RejectedWithoutWrite:SyntheticInboxExistingDealOutcome;data object Unknown:SyntheticInboxExistingDealOutcome}
interface SyntheticInboxExistingDealPort {val grants:List<SyntheticInboxExistingDealGrant>;suspend fun execute(a:InboxExistingDealAttempt):SyntheticInboxExistingDealOutcome}
enum class InboxExistingDealPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxExistingDealRecord(val attempt:InboxExistingDealAttempt,val phase:InboxExistingDealPhase,val result:InboxExistingDealReceipt?=null)
class InboxExistingDealLedger {
    private val history=mutableListOf<InboxExistingDealRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxExistingDealAuthorization?):InboxExistingDealRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxExistingDealReview):InboxExistingDealAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxExistingDealAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxExistingDealRecord(a,InboxExistingDealPhase.PENDING));return a}
    fun complete(a:InboxExistingDealAttempt,outcome:SyntheticInboxExistingDealOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxExistingDealPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxExistingDealOutcome.Unknown->history[i].copy(phase=InboxExistingDealPhase.UNKNOWN);SyntheticInboxExistingDealOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxExistingDealPhase.REJECTED);is SyntheticInboxExistingDealOutcome.Response->{val r=if(outcome.status==200)InboxExistingDealReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxExistingDealPhase.UNKNOWN else InboxExistingDealPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxExistingDealAuthorization,record:InboxExistingDealRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxExistingDealPhase.RESPONSE,InboxExistingDealPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
