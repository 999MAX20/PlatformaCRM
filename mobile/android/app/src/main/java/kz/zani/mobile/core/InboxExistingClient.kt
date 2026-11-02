package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Source projection only, not the link command/picker/authority.
typealias InboxExistingClientSource = InboxLinkClientSource
data class SyntheticInboxExistingClientGrant(val business:Int,val conversation:Int,val actor:Int,val clientsCreate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && clientsCreate && conversationsUpdate)SyntheticInboxExistingClientAuthorization.create(c,actor)else null
}
data class SyntheticInboxExistingClientAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxExistingClientAuthorization(c,actor)}}
data class InboxExistingClientReview(val source:InboxExistingClientSource,val authorization:SyntheticInboxExistingClientAuthorization,val visit:Int) {val valid get()=source.valid && source.client?.let {it>0}==true && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxExistingClientAttempt internal constructor(val localID:Int,val review:InboxExistingClientReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/create-client/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
// Existing ClientSerializer identity only, never annotation/count or actor authority.
data class InboxExistingClientReceipt private constructor(val id:Int,val business:Int,val fullName:String,val phone:String,val email:String,val updatedAt:String) {
    companion object {fun decode(body:String,a:InboxExistingClientAttempt):InboxExistingClientReceipt?=runCatching {
        require(a.review.valid);val t=JSONTokener(body);val root=t.nextValue();require(t.nextClean()=='\u0000' && root is JSONObject);val created=root.get("created");require(created is Boolean && !created && root.getJSONArray("duplicates").length()==0 && !root.has("requires_confirmation"));val row=root.getJSONObject("client");val id=a.review.source.client!!;require(directoryReadInteger(row.get("id"))==id.toLong() && directoryReadInteger(row.get("business"))==a.review.source.context.business.toLong());val name=row.get("full_name");val phone=row.get("phone");val email=row.get("email");val updated=row.get("updated_at");require(name is String && phone is String && email is String && updated is String && updated.isNotEmpty());InboxExistingClientReceipt(id,a.review.source.context.business,name,phone,email,updated)
    }.getOrNull()}
}
sealed interface SyntheticInboxExistingClientOutcome {data class Response(val status:Int,val body:String):SyntheticInboxExistingClientOutcome;data object RejectedWithoutWrite:SyntheticInboxExistingClientOutcome;data object Unknown:SyntheticInboxExistingClientOutcome}
interface SyntheticInboxExistingClientPort {val grants:List<SyntheticInboxExistingClientGrant>;suspend fun execute(a:InboxExistingClientAttempt):SyntheticInboxExistingClientOutcome}
enum class InboxExistingClientPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxExistingClientRecord(val attempt:InboxExistingClientAttempt,val phase:InboxExistingClientPhase,val result:InboxExistingClientReceipt?=null)
class InboxExistingClientLedger {
    private val history=mutableListOf<InboxExistingClientRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxExistingClientAuthorization?):InboxExistingClientRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxExistingClientReview):InboxExistingClientAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxExistingClientAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxExistingClientRecord(a,InboxExistingClientPhase.PENDING));return a}
    fun complete(a:InboxExistingClientAttempt,outcome:SyntheticInboxExistingClientOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxExistingClientPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxExistingClientOutcome.Unknown->history[i].copy(phase=InboxExistingClientPhase.UNKNOWN);SyntheticInboxExistingClientOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxExistingClientPhase.REJECTED);is SyntheticInboxExistingClientOutcome.Response->{val r=if(outcome.status==200)InboxExistingClientReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxExistingClientPhase.UNKNOWN else InboxExistingClientPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxExistingClientAuthorization,record:InboxExistingClientRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxExistingClientPhase.RESPONSE,InboxExistingClientPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
