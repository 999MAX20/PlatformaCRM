package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Generic conversation relation projection only. No CREATE/UPDATE/actor/default inference.
data class InboxTaskSource private constructor(val context:InboxConversationFilesContext,val client:Int?,val lead:Int?,val updatedAt:String) {
    val valid get()=context.valid && updatedAt.isNotEmpty() && listOf(client,lead).all {it==null || it>0}
    companion object {fun decode(body:String,c:InboxConversationFilesContext):InboxTaskSource?=runCatching {
        val t=JSONTokener(body);val row=t.nextValue();require(t.nextClean()=='\u0000' && row is JSONObject && c.valid);require(directoryReadInteger(row.get("id"))==c.conversation.toLong() && directoryReadInteger(row.get("business"))==c.business.toLong());val updated=row.get("updated_at");require(updated is String && updated.isNotEmpty())
        fun optional(key:String):Int? {require(row.has(key));if(row.isNull(key))return null;return directoryReadInteger(row.get(key))!!.also {require(it>0 && it<=Int.MAX_VALUE)}.toInt()}
        InboxTaskSource(c,optional("client"),optional("lead"),updated)
    }.getOrNull()}
}
data class InboxTaskSourceControl(val context:InboxConversationFilesContext,val visit:Int)
data class InboxTaskSourceTicket(val context:InboxConversationFilesContext,val revision:Int)
data class QualifiedInboxTaskSource internal constructor(val source:InboxTaskSource,val readRevision:Int) {val context get()=source.context;val valid get()=source.valid && readRevision>0}
data class InboxTaskSourceState(val context:InboxConversationFilesContext?=null,val presented:Boolean=false,val loading:Boolean=false,val source:InboxTaskSource?=null,val problem:ReadProblem?=null,val choice:QualifiedInboxTaskSource?=null)
class InboxTaskSourceSession {
    var state=InboxTaskSourceState();private set
    private var pending:InboxTaskSourceTicket?=null;private var revision=0;private var visit=0;private var sourceRevision=0
    val control get()=state.context?.let {InboxTaskSourceControl(it,visit)}
    val canRead get()=state.presented && !state.loading && state.context!=null
    val canUse get()=state.presented && !state.loading && state.problem==null && state.source?.context==state.context && state.source?.valid==true && sourceRevision>0
    private fun invalidate(){++revision;++visit;sourceRevision=0;pending=null;state=state.copy(loading=false,source=null,problem=null,choice=null)}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==state.context)return;hide();state=state.copy(context=next)}
    fun show(){if(state.context==null || state.presented)return;invalidate();state=state.copy(presented=true)}
    fun hide(){invalidate();state=state.copy(presented=false)}
    fun begin(expected:InboxTaskSourceControl?):InboxTaskSourceTicket? {if(expected==null || control!=expected || !canRead)return null;val c=state.context ?: return null;invalidate();state=state.copy(loading=true);return InboxTaskSourceTicket(c,revision).also {pending=it}}
    fun accept(source:InboxTaskSource,ticket:InboxTaskSourceTicket):Boolean {if(pending!=ticket || !state.presented || state.context!=ticket.context)return false;if(!source.valid || source.context!=ticket.context){fail(ReadProblem.INVALID_PAYLOAD,ticket);return false};pending=null;sourceRevision=ticket.revision;++visit;state=state.copy(loading=false,source=source,problem=null);return true}
    fun fail(problem:ReadProblem,ticket:InboxTaskSourceTicket){if(pending!=ticket || !state.presented || state.context!=ticket.context)return;pending=null;sourceRevision=0;++visit;state=state.copy(loading=false,source=null,problem=problem,choice=null)}
    fun cancel(ticket:InboxTaskSourceTicket){if(pending==ticket)invalidate()}
    fun use(expected:InboxTaskSourceControl?){if(expected==null || control!=expected || !canUse)return;val source=state.source ?: return;++visit;state=state.copy(choice=QualifiedInboxTaskSource(source,sourceRevision))}
    fun clearChoice(expected:InboxTaskSourceControl?){if(expected==null || control!=expected || !state.presented || state.loading)return;++visit;state=state.copy(choice=null)}
}
