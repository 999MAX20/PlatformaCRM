package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxLinkDealSource private constructor(val context:InboxConversationFilesContext,val deal:Int?,val client:Int?,val lead:Int?,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty() && listOf(deal,client,lead).all {it==null || it>0}
    companion object {fun decode(body:String,c:InboxConversationFilesContext):InboxLinkDealSource?=runCatching {
        val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong());val updated=row.get("updated_at");require(updated is String && updated.isNotEmpty())
        fun optional(key:String):Int? {require(row.has(key));if(row.isNull(key))return null;return directoryReadInteger(row.get(key))!!.also {require(it>0 && it<=Int.MAX_VALUE)}.toInt()}
        val client=when(val read=TaskCreateClientRead.decode(body)){TaskCreateClientRead.Unknown->error("client missing or invalid");TaskCreateClientRead.NotSet->null;is TaskCreateClientRead.Client->read.id};InboxLinkDealSource(c,optional("deal"),client,optional("lead"),updated)
    }.getOrNull()}
}
data class InboxLinkDealCandidate private constructor(val source:InboxLinkDealSource,val reference:QualifiedDealReference) {
    val valid get()=source.valid && reference.valid && reference.context==source.context
    companion object {fun make(source:InboxLinkDealSource,reference:QualifiedDealReference):InboxLinkDealCandidate? {if(!source.valid || !reference.valid || reference.context!=source.context)return null;return InboxLinkDealCandidate(source,reference)}}
}
data class SyntheticInboxLinkDealGrant(val business:Int,val conversation:Int,val actor:Int,val dealsUpdate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && dealsUpdate && conversationsUpdate)SyntheticInboxLinkDealAuthorization.create(c,actor)else null
}
data class SyntheticInboxLinkDealAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxLinkDealAuthorization(c,actor)}}
data class InboxLinkDealReview(val source:InboxLinkDealSource,val authorization:SyntheticInboxLinkDealAuthorization,val candidate:InboxLinkDealCandidate,val visit:Int) {val valid get()=source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxLinkDealAttempt internal constructor(val localID:Int,val review:InboxLinkDealReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/link-deal/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{\"deal_id\":${review.candidate.reference.source.id}}"
}
data class InboxLinkDealReceipt private constructor(val source:InboxLinkDealSource) {companion object {fun decode(body:String,a:InboxLinkDealAttempt):InboxLinkDealReceipt? {if(!a.review.valid)return null;val s=InboxLinkDealSource.decode(body,a.review.source.context) ?: return null;val ref=a.review.candidate.reference.source;return if(s.deal==ref.id && s.client==(a.review.source.client ?: ref.client) && s.lead==(a.review.source.lead ?: ref.lead))InboxLinkDealReceipt(s)else null}}}
sealed interface SyntheticInboxLinkDealOutcome {data class Response(val status:Int,val body:String):SyntheticInboxLinkDealOutcome;data object RejectedWithoutWrite:SyntheticInboxLinkDealOutcome;data object Unknown:SyntheticInboxLinkDealOutcome}
interface SyntheticInboxLinkDealPort {val grants:List<SyntheticInboxLinkDealGrant>;suspend fun execute(a:InboxLinkDealAttempt):SyntheticInboxLinkDealOutcome}
enum class InboxLinkDealPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxLinkDealRecord(val attempt:InboxLinkDealAttempt,val phase:InboxLinkDealPhase,val result:InboxLinkDealReceipt?=null)
class InboxLinkDealLedger {
    private val history=mutableListOf<InboxLinkDealRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxLinkDealAuthorization?):InboxLinkDealRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxLinkDealReview):InboxLinkDealAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxLinkDealAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxLinkDealRecord(a,InboxLinkDealPhase.PENDING));return a}
    fun complete(a:InboxLinkDealAttempt,outcome:SyntheticInboxLinkDealOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxLinkDealPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxLinkDealOutcome.Unknown->history[i].copy(phase=InboxLinkDealPhase.UNKNOWN);SyntheticInboxLinkDealOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxLinkDealPhase.REJECTED);is SyntheticInboxLinkDealOutcome.Response->{val r=if(outcome.status==200)InboxLinkDealReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxLinkDealPhase.UNKNOWN else InboxLinkDealPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxLinkDealAuthorization,record:InboxLinkDealRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxLinkDealPhase.RESPONSE,InboxLinkDealPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
