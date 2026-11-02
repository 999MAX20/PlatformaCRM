package kz.zani.mobile.core
import org.json.JSONObject
import org.json.JSONTokener

// Narrow generic DealSerializer lens. No mobile alias, command grant or server version.
data class DealReadSource private constructor(val id:Int,val business:Int,val client:Int,val lead:Int?,val title:String,val updatedAt:String) {
    fun validFor(scope:Int,id:Int)=scope>0 && id>0 && business==scope && this.id==id && client>0 && (lead==null || lead>0) && updatedAt.isNotEmpty()
    companion object {fun decode(raw:String,business:Int,id:Int):DealReadSource?=runCatching {require(business>0 && id>0);val t=JSONTokener(raw);val o=t.nextValue();require(t.nextClean()=='\u0000' && o is JSONObject);require(directoryReadInteger(o.get("id"))==id.toLong() && directoryReadInteger(o.get("business"))==business.toLong());val client=directoryReadInteger(o.get("client"))!!;require(client>0 && client<=Int.MAX_VALUE && o.has("lead"));val lead=if(o.isNull("lead"))null else directoryReadInteger(o.get("lead"))!!.also {require(it>0 && it<=Int.MAX_VALUE)}.toInt();val title=o.get("title");val updated=o.get("updated_at");require(title is String && updated is String && updated.isNotEmpty());DealReadSource(id,business,client.toInt(),lead,title,updated)}.getOrNull()}
}
object DealReferenceIdentifier {fun parse(raw:String):Int?=raw.takeIf {it.isNotEmpty() && it.all {c->c in '0'..'9'}}?.toIntOrNull()?.takeIf {it>0}}
data class DealReferenceControl(val context:InboxConversationFilesContext,val visit:Int)
data class DealReferenceInput(val context:InboxConversationFilesContext,val generation:Int)
data class DealReferenceTicket(val context:InboxConversationFilesContext,val revision:Int,val rawInput:String,val id:Int)
data class QualifiedDealReference internal constructor(val context:InboxConversationFilesContext,val readRevision:Int,val rawInput:String,val source:DealReadSource) {val valid get()=context.valid && readRevision>0 && DealReferenceIdentifier.parse(rawInput)==source.id && source.validFor(context.business,source.id)}
data class DealReferenceState(val context:InboxConversationFilesContext?=null,val presented:Boolean=false,val rawInput:String="",val loading:Boolean=false,val source:DealReadSource?=null,val problem:ReadProblem?=null,val choice:QualifiedDealReference?=null) {
    val invalidIdentifier get()=rawInput.isNotEmpty() && DealReferenceIdentifier.parse(rawInput)==null
    val canRead get()=presented && !loading && DealReferenceIdentifier.parse(rawInput)!=null
}
class DealReferenceSession {
    var state=DealReferenceState();private set
    private var pending:DealReferenceTicket?=null;private var revision=0;private var visit=0;private var inputGeneration=0;private var sourceRevision=0
    val control get()=state.context?.let {DealReferenceControl(it,visit)}
    val input get()=state.context?.let {if(state.presented)DealReferenceInput(it,inputGeneration)else null}
    val canUse get()=state.presented && !state.loading && state.problem==null && sourceRevision>0 && state.source?.let {DealReferenceIdentifier.parse(state.rawInput)==it.id && it.validFor(state.context?.business ?: 0,it.id)}==true
    private fun invalidate(){++revision;++visit;sourceRevision=0;pending=null;state=state.copy(loading=false,source=null,problem=null,choice=null)}
    fun bind(next:InboxConversationFilesContext?){val next=next?.takeIf {it.valid};if(next==state.context)return;hide();state=state.copy(context=next,rawInput="")}
    fun show(){if(state.context==null || state.presented)return;invalidate();++inputGeneration;state=state.copy(presented=true)}
    fun hide(){invalidate();++inputGeneration;state=state.copy(presented=false)}
    fun update(raw:String,input:DealReferenceInput?){if(input==null || this.input!=input || raw==state.rawInput)return;invalidate();state=state.copy(rawInput=raw)}
    fun clear(expected:DealReferenceControl?){if(expected==null || control!=expected || !state.presented)return;invalidate();++inputGeneration;state=state.copy(rawInput="")}
    fun begin(expected:DealReferenceControl?):DealReferenceTicket? {val c=state.context ?: return null;val id=DealReferenceIdentifier.parse(state.rawInput) ?: return null;if(expected==null || control!=expected || !state.canRead)return null;invalidate();state=state.copy(loading=true);return DealReferenceTicket(c,revision,state.rawInput,id).also {pending=it}}
    fun accept(source:DealReadSource,ticket:DealReferenceTicket):Boolean {if(pending!=ticket || !state.presented || state.context!=ticket.context)return false;if(!source.validFor(ticket.context.business,ticket.id)){fail(ReadProblem.INVALID_PAYLOAD,ticket);return false};pending=null;sourceRevision=ticket.revision;state=state.copy(loading=false,problem=null,source=source);++visit;return true}
    fun fail(problem:ReadProblem,ticket:DealReferenceTicket){if(pending!=ticket || !state.presented || state.context!=ticket.context)return;pending=null;sourceRevision=0;state=state.copy(loading=false,source=null,problem=problem,choice=null);++visit}
    fun cancel(ticket:DealReferenceTicket){if(pending!=ticket)return;pending=null;sourceRevision=0;state=state.copy(loading=false,source=null,problem=null,choice=null);++visit}
    fun use(expected:DealReferenceControl?){val c=state.context ?: return;val source=state.source ?: return;if(expected==null || control!=expected || !canUse)return;state=state.copy(choice=QualifiedDealReference(c,sourceRevision,state.rawInput,source));++visit}
    fun clearChoice(expected:DealReferenceControl?){if(expected==null || control!=expected || !state.presented || state.loading)return;state=state.copy(choice=null);++visit}
}
