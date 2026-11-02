package kz.zani.mobile.core

import org.json.JSONObject
import org.json.JSONTokener

// Narrow raw read projection. No permission, version, parsed date or recovery inference.
data class InboxLinkClientSource private constructor(val context:InboxConversationFilesContext,val client:Int?,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty() && (client==null || client>0)
    companion object {
        fun decode(body:String,c:InboxConversationFilesContext):InboxLinkClientSource?=runCatching {val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong());val updated=row.get("updated_at");require(updated is String && updated.isNotEmpty());val value=when(val read=TaskCreateClientRead.decode(body)){TaskCreateClientRead.Unknown->error("client missing or invalid");TaskCreateClientRead.NotSet->null;is TaskCreateClientRead.Client->read.id};InboxLinkClientSource(c,value,updated)}.getOrNull()
    }
}
data class InboxLinkClientCandidate private constructor(val source:InboxLinkClientSource,val selected:ClientSearchProfileSelection,val read:ClientReadSelection,val rawQuery:String,val choice:TaskDraftClientChoice) {
    val valid get()=source.valid && choice.validFor(source.context.business) && selected.selection.generation>0 && selected.generation>0 && selected.id==choice.id && read.id==choice.id && read.business==choice.business && read.revision>0 && selected.selection.context==ClientSearchContext(source.context.business,source.context.epoch)
    companion object {fun make(source:InboxLinkClientSource,selected:ClientSearchProfileSelection,read:ClientReadSelection,rawQuery:String,profile:ClientProfile):InboxLinkClientCandidate? {val c=source.context;val choice=TaskDraftClientChoice.make(profile,c.business,selected.id) ?: return null;if(!source.valid || selected.selection.context!=ClientSearchContext(c.business,c.epoch) || selected.selection.generation<=0 || selected.generation<=0 || read.business!=c.business || read.id!=selected.id || read.revision<=0)return null;return InboxLinkClientCandidate(source,selected,read,rawQuery,choice)}}
}
data class SyntheticInboxLinkClientGrant(val business:Int,val conversation:Int,val actor:Int,val clientsUpdate:Boolean,val conversationsUpdate:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && clientsUpdate && conversationsUpdate)SyntheticInboxLinkClientAuthorization.create(c,actor)else null
}
data class SyntheticInboxLinkClientAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxLinkClientAuthorization(c,actor)}}
data class InboxLinkClientReview(val source:InboxLinkClientSource,val authorization:SyntheticInboxLinkClientAuthorization,val candidate:InboxLinkClientCandidate,val visit:Int) {val valid get()=source.valid && candidate.valid && candidate.source==source && authorization.context==source.context && authorization.actor>0 && visit>0}
data class InboxLinkClientAttempt internal constructor(val localID:Int,val review:InboxLinkClientReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/link-client/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{\"client_id\":${review.candidate.choice.id}}"
}
data class InboxLinkClientReceipt private constructor(val source:InboxLinkClientSource) {companion object {fun decode(body:String,a:InboxLinkClientAttempt):InboxLinkClientReceipt? {if(!a.review.valid)return null;val s=InboxLinkClientSource.decode(body,a.review.source.context) ?: return null;return if(s.client==a.review.candidate.choice.id)InboxLinkClientReceipt(s)else null}}}
sealed interface SyntheticInboxLinkClientOutcome {data class Response(val status:Int,val body:String):SyntheticInboxLinkClientOutcome;data object RejectedWithoutWrite:SyntheticInboxLinkClientOutcome;data object Unknown:SyntheticInboxLinkClientOutcome}
interface SyntheticInboxLinkClientPort {val grants:List<SyntheticInboxLinkClientGrant>;suspend fun execute(a:InboxLinkClientAttempt):SyntheticInboxLinkClientOutcome}
enum class InboxLinkClientPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxLinkClientRecord(val attempt:InboxLinkClientAttempt,val phase:InboxLinkClientPhase,val result:InboxLinkClientReceipt?=null)
class InboxLinkClientLedger {
    private val history=mutableListOf<InboxLinkClientRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxLinkClientAuthorization?):InboxLinkClientRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxLinkClientReview):InboxLinkClientAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxLinkClientAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxLinkClientRecord(a,InboxLinkClientPhase.PENDING));return a}
    fun complete(a:InboxLinkClientAttempt,outcome:SyntheticInboxLinkClientOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxLinkClientPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxLinkClientOutcome.Unknown->history[i].copy(phase=InboxLinkClientPhase.UNKNOWN);SyntheticInboxLinkClientOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxLinkClientPhase.REJECTED);is SyntheticInboxLinkClientOutcome.Response->{val r=if(outcome.status==200)InboxLinkClientReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxLinkClientPhase.UNKNOWN else InboxLinkClientPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxLinkClientAuthorization,record:InboxLinkClientRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxLinkClientPhase.RESPONSE,InboxLinkClientPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
