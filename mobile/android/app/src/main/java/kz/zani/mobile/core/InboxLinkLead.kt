package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxLinkLeadSource private constructor(val context:InboxConversationFilesContext,val lead:Int?,val client:Int?,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty() && (lead==null || lead>0) && (client==null || client>0)
    companion object {fun decode(body:String,c:InboxConversationFilesContext):InboxLinkLeadSource?=runCatching {
        val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong());val updated=row.get("updated_at");require(updated is String && updated.isNotEmpty() && row.has("lead"));val lead=if(row.isNull("lead"))null else directoryReadInteger(row.get("lead"))!!.also {require(it>0 && it<=Int.MAX_VALUE)}.toInt()
        val client=when(val read=TaskCreateClientRead.decode(body)){TaskCreateClientRead.Unknown->error("client missing or invalid");TaskCreateClientRead.NotSet->null;is TaskCreateClientRead.Client->read.id};InboxLinkLeadSource(c,lead,client,updated)
    }.getOrNull()}
}
data class InboxLinkLeadCandidate private constructor(val source:InboxLinkLeadSource,val reference:QualifiedLeadReference) {
    val valid get()=source.valid && reference.context==source.context && reference.readRevision>0 && reference.detail.validFor(source.context.business,reference.detail.lead.id)
    companion object {fun make(source:InboxLinkLeadSource,reference:QualifiedLeadReference):InboxLinkLeadCandidate? {if(!source.valid || reference.context!=source.context || reference.readRevision<=0 || !reference.detail.validFor(source.context.business,reference.detail.lead.id))return null;return InboxLinkLeadCandidate(source,reference)}}
}
data class SyntheticInboxLinkLeadGrant(val business:Int,val conversation:Int,val actor:Int,val leadsUpdate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && leadsUpdate && conversationsUpdate)SyntheticInboxLinkLeadAuthorization.create(c,actor)else null
}
data class SyntheticInboxLinkLeadAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxLinkLeadAuthorization(c,actor)}}
data class InboxLinkLeadReview(val source:InboxLinkLeadSource,val authorization:SyntheticInboxLinkLeadAuthorization,val candidate:InboxLinkLeadCandidate,val visit:Int) {val valid get()=source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxLinkLeadAttempt internal constructor(val localID:Int,val review:InboxLinkLeadReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/link-lead/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{\"lead_id\":${review.candidate.reference.detail.lead.id}}"
}
data class InboxLinkLeadReceipt private constructor(val source:InboxLinkLeadSource) {companion object {fun decode(body:String,a:InboxLinkLeadAttempt):InboxLinkLeadReceipt? {if(!a.review.valid)return null;val s=InboxLinkLeadSource.decode(body,a.review.source.context) ?: return null;return if(s.lead==a.review.candidate.reference.detail.lead.id && s.client==(a.review.source.client ?: a.review.candidate.reference.detail.lead.client_id))InboxLinkLeadReceipt(s)else null}}}
sealed interface SyntheticInboxLinkLeadOutcome {data class Response(val status:Int,val body:String):SyntheticInboxLinkLeadOutcome;data object RejectedWithoutWrite:SyntheticInboxLinkLeadOutcome;data object Unknown:SyntheticInboxLinkLeadOutcome}
interface SyntheticInboxLinkLeadPort {val grants:List<SyntheticInboxLinkLeadGrant>;suspend fun execute(a:InboxLinkLeadAttempt):SyntheticInboxLinkLeadOutcome}
enum class InboxLinkLeadPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxLinkLeadRecord(val attempt:InboxLinkLeadAttempt,val phase:InboxLinkLeadPhase,val result:InboxLinkLeadReceipt?=null)
class InboxLinkLeadLedger {
    private val history=mutableListOf<InboxLinkLeadRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxLinkLeadAuthorization?):InboxLinkLeadRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxLinkLeadReview):InboxLinkLeadAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxLinkLeadAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxLinkLeadRecord(a,InboxLinkLeadPhase.PENDING));return a}
    fun complete(a:InboxLinkLeadAttempt,outcome:SyntheticInboxLinkLeadOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxLinkLeadPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxLinkLeadOutcome.Unknown->history[i].copy(phase=InboxLinkLeadPhase.UNKNOWN);SyntheticInboxLinkLeadOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxLinkLeadPhase.REJECTED);is SyntheticInboxLinkLeadOutcome.Response->{val r=if(outcome.status==200)InboxLinkLeadReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxLinkLeadPhase.UNKNOWN else InboxLinkLeadPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxLinkLeadAuthorization,record:InboxLinkLeadRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxLinkLeadPhase.RESPONSE,InboxLinkLeadPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
