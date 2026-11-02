package kz.zani.mobile.core

import java.util.Locale

data class QuickReplyTemplate(val id: Int,val business: Int,val title: String,val text: String,val category: String,val channel: String,val sortOrder: Int,val isActive: Boolean)
data class QuickReplyPage(val items: List<QuickReplyTemplate>,val count: Int?,val hasNext: Boolean,val metadataKnown: Boolean) {
    val partial get()=!metadataKnown || hasNext || (count ?: items.size)>items.size
    fun validFor(context: QuickReplyContext)=context.valid && (count==null || count>=items.size) && items.map {it.id}.distinct().size==items.size && items.all {it.id>0 && it.business==context.draft.context.business && it.isActive && it.sortOrder>=0 && it.channel in listOf("all",context.channel) && SourceTextTrim.pythonStrip(it.text).isNotEmpty()}
}
data class QuickReplyContext(val draft: ReplyDraftSelection,val channel: String) {
    companion object {val channels=listOf("website","telegram","whatsapp","instagram")}
    val valid get()=draft.context.valid && draft.generation>0 && channel in channels
}
data class QuickReplySelection(val context: QuickReplyContext,val generation: Int)
data class QuickReplyRequest(val selection: QuickReplySelection,val revision: Int)
data class QuickReplyChoice(val request: QuickReplyRequest,val filterRevision: Int,val template: QuickReplyTemplate)
object QuickReplyInsertion {
    fun text(draft: String,template: String)=if(SourceTextTrim.javascriptTrim(draft).isEmpty())template else SourceTextTrim.javascriptTrimEnd(draft)+"\n"+template
}
data class QuickReplyState(val context: QuickReplyContext?=null,val selection: QuickReplySelection?=null,val query: String="",val items: List<QuickReplyTemplate> = emptyList(),val partial: Boolean=false,val loading: Boolean=false,val loaded: Boolean=false,val problem: ReadProblem?=null)
class QuickReplySession {
    var state=QuickReplyState();private set
    private var generation=0;private var revision=0;private var filterRevision=0
    private var pending: QuickReplyRequest?=null;private var accepted: QuickReplyRequest?=null
    val choices: List<QuickReplyChoice> get() {
        val accepted=accepted ?: return emptyList()
        if(state.selection!=accepted.selection || !state.loaded || state.loading || state.problem!=null)return emptyList()
        val needle=SourceTextTrim.javascriptTrim(state.query).lowercase(Locale.ROOT)
        return state.items.filter {needle.isEmpty() || (it.title+" "+it.text+" "+it.category).lowercase(Locale.ROOT).contains(needle)}.map {QuickReplyChoice(accepted,filterRevision,it)}
    }
    val showsEmpty get()=state.loaded && !state.loading && state.problem==null && !state.partial && choices.isEmpty()
    private fun invalidate() {++revision;pending=null;accepted=null;state=state.copy(items=emptyList(),partial=false,loading=false,loaded=false,problem=null)}
    fun bind(next: QuickReplyContext?) {
        val next=next?.takeIf {it.valid}
        if(next==state.context)return
        invalidate();++generation;++filterRevision;state=QuickReplyState(context=next)
    }
    fun open(expected: QuickReplyContext): QuickReplyRequest? {
        if(state.context!=expected || !expected.valid)return null
        invalidate();val selected=QuickReplySelection(expected,++generation);state=state.copy(selection=selected,loading=true)
        return QuickReplyRequest(selected,revision).also {pending=it}
    }
    fun retry(expected: QuickReplySelection): QuickReplyRequest? {
        if(state.selection!=expected)return null
        invalidate();state=state.copy(loading=true);return QuickReplyRequest(expected,revision).also {pending=it}
    }
    fun accept(page: QuickReplyPage,request: QuickReplyRequest) {
        if(pending!=request || state.selection!=request.selection)return
        if(!page.validFor(request.selection.context)) {fail(ReadProblem.INVALID_PAYLOAD,request);return}
        pending=null;accepted=request;state=state.copy(items=page.items,partial=page.partial,loading=false,loaded=true,problem=null)
    }
    fun fail(problem: ReadProblem,request: QuickReplyRequest) {
        if(pending!=request || state.selection!=request.selection)return
        invalidate();state=state.copy(problem=problem)
    }
    fun cancel(request: QuickReplyRequest) {if(pending==request && state.selection==request.selection)invalidate()}
    fun search(value: String,expected: QuickReplySelection) {
        // Raw query changes revoke prior choices even for NFC/NFD-equivalent text.
        if(state.selection!=expected || state.query==value)return
        ++filterRevision;state=state.copy(query=value)
    }
    fun resolve(choice: QuickReplyChoice): String?=choice.takeIf {it in choices}?.template?.text
    fun close(expected: QuickReplySelection) {
        if(state.selection!=expected)return
        invalidate();++generation;state=state.copy(selection=null)
    }
}
