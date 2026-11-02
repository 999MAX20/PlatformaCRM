package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Explicit synthetic TASKS.CREATE context, independent of GET and other task endpoints.
data class SyntheticInboxCreateTaskGrant(val business:Int,val conversation:Int,val actor:Int,val create:Boolean) {
    fun authorization(c:InboxConversationFilesContext)=if(c.valid && business==c.business && conversation==c.conversation && actor>0 && create)SyntheticInboxCreateTaskAuthorization.create(c,actor)else null
}
data class SyntheticInboxCreateTaskAuthorization private constructor(val context:InboxConversationFilesContext,val actor:Int) {companion object {internal fun create(c:InboxConversationFilesContext,actor:Int)=SyntheticInboxCreateTaskAuthorization(c,actor)}}
data class InboxCreateTaskReview(val reference:QualifiedInboxTaskSource,val authorization:SyntheticInboxCreateTaskAuthorization,val visit:Int) {val source get()=reference.source;val valid get()=reference.valid && authorization.context==reference.context && authorization.actor>0 && visit>0}
data class InboxCreateTaskAttempt internal constructor(val localID:Int,val review:InboxCreateTaskReview) {
    val path get()="/api/inbox/conversations/${review.source.context.conversation}/create-task/"
    val query:Map<String,String> get()=emptyMap();val headers:Map<String,String> get()=emptyMap()
    fun preparedBody()="{}"
}
// Existing generic TaskSerializer result projection; title is observed, not reconstructed.
data class InboxCreateTaskReceipt private constructor(val id:Int,val business:Int,val title:String,val description:String,val client:Int?,val lead:Int?,val assignee:Int,val createdBy:Int,val priority:String,val dueAt:String?,val updatedAt:String) {
    companion object {fun decode(body:String,a:InboxCreateTaskAttempt):InboxCreateTaskReceipt?=runCatching {
        require(a.review.valid);val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject)
        val id=directoryReadInteger(row.get("id"));require(id!=null && id>0 && id<=Int.MAX_VALUE);val original=a.review.source;val actor=a.review.authorization.actor
        require(directoryReadInteger(row.get("business"))==original.context.business.toLong() && directoryReadInteger(row.get("assignee"))==actor.toLong() && directoryReadInteger(row.get("created_by"))==actor.toLong())
        val title=row.get("title");val description=row.get("description");val priority=row.get("priority");val updated=row.get("updated_at");require(title is String && title.isNotEmpty() && description is String && description.isEmpty() && priority is String && priority=="normal" && updated is String && updated.isNotEmpty() && row.has("due_at") && row.isNull("due_at"))
        for((key,value) in listOf("client" to original.client,"lead" to original.lead)){require(row.has(key));if(value==null)require(row.isNull(key))else require(directoryReadInteger(row.get(key))==value.toLong())}
        InboxCreateTaskReceipt(id.toInt(),original.context.business,title,description,original.client,original.lead,actor,actor,priority,null,updated)
    }.getOrNull()}
}
sealed interface SyntheticInboxCreateTaskOutcome {data class Response(val status:Int,val body:String):SyntheticInboxCreateTaskOutcome;data object RejectedWithoutWrite:SyntheticInboxCreateTaskOutcome;data object Unknown:SyntheticInboxCreateTaskOutcome}
interface SyntheticInboxCreateTaskPort {val grants:List<SyntheticInboxCreateTaskGrant>;suspend fun execute(a:InboxCreateTaskAttempt):SyntheticInboxCreateTaskOutcome}
enum class InboxCreateTaskPhase {PENDING,RESPONSE,REJECTED,UNKNOWN}
data class InboxCreateTaskRecord(val attempt:InboxCreateTaskAttempt,val phase:InboxCreateTaskPhase,val result:InboxCreateTaskReceipt?=null)
class InboxCreateTaskLedger {
    private val history=mutableListOf<InboxCreateTaskRecord>();val records get()=history.toList();private val active=mutableMapOf<Pair<Int,Int>,Int>()
    private fun key(c:InboxConversationFilesContext)=c.business to c.conversation
    fun blocked(business:Int,conversation:Int)=active.containsKey(business to conversation)
    fun visible(auth:SyntheticInboxCreateTaskAuthorization?):InboxCreateTaskRecord? {auth ?: return null;val i=active[key(auth.context)] ?: return null;return history[i].takeIf {it.attempt.review.authorization.actor==auth.actor}}
    fun begin(review:InboxCreateTaskReview):InboxCreateTaskAttempt? {val c=review.source.context;if(!review.valid || blocked(c.business,c.conversation))return null;val a=InboxCreateTaskAttempt(history.size+1,review);active[key(c)]=history.size;history.add(InboxCreateTaskRecord(a,InboxCreateTaskPhase.PENDING));return a}
    fun complete(a:InboxCreateTaskAttempt,outcome:SyntheticInboxCreateTaskOutcome) {
        val i=history.indexOfFirst {it.attempt==a};if(i<0 || history[i].phase!=InboxCreateTaskPhase.PENDING)return
        history[i]=when(outcome) {SyntheticInboxCreateTaskOutcome.Unknown->history[i].copy(phase=InboxCreateTaskPhase.UNKNOWN);SyntheticInboxCreateTaskOutcome.RejectedWithoutWrite->history[i].copy(phase=InboxCreateTaskPhase.REJECTED);is SyntheticInboxCreateTaskOutcome.Response->{val r=if(outcome.status==201)InboxCreateTaskReceipt.decode(outcome.body,a)else null;history[i].copy(phase=if(r==null)InboxCreateTaskPhase.UNKNOWN else InboxCreateTaskPhase.RESPONSE,result=r)}}
    }
    fun acknowledge(auth:SyntheticInboxCreateTaskAuthorization,record:InboxCreateTaskRecord):Boolean {if(visible(auth)!=record || record.phase !in listOf(InboxCreateTaskPhase.RESPONSE,InboxCreateTaskPhase.REJECTED))return false;active.remove(key(auth.context));return true}
}
