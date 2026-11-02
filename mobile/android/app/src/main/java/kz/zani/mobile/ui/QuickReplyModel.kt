package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.QuickReplyRepository

// Local UI visits only; no new catalogue or request contract.
data class QuickReplyEntryControl(val context:QuickReplyContext,val visit:Int)
data class QuickReplyControl(val selection:QuickReplySelection,val visit:Int)
data class QuickReplyInputControl(val selection:QuickReplySelection,val visit:Int)
class QuickReplyModel(private val repository: QuickReplyRepository,private val ownerScope: CoroutineScope) {
    private val session=QuickReplySession()
    var state by mutableStateOf(session.state);private set
    private var entryVisit by mutableStateOf(0)
    private var windowVisit by mutableStateOf(0)
    private var inputVisit by mutableStateOf(0)
    private var readRevision=0
    val choices get()=session.choices
    val showsEmpty get()=session.showsEmpty
    val entryControl get()=state.context?.takeIf {state.selection==null}?.let {QuickReplyEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {QuickReplyControl(it,windowVisit)}
    val inputControl get()=state.selection?.let {QuickReplyInputControl(it,inputVisit)}
    private fun invalidateVisit() {entryVisit++;windowVisit++;inputVisit++;readRevision++}
    fun bind(context: QuickReplyContext?) {
        val before=state.context;val selection=state.selection;session.bind(context);state=session.state
        if(before!=state.context || selection!=state.selection)invalidateVisit()
    }
    // Raw trusted APIs retained; UI uses the captured overloads below.
    fun open(context: QuickReplyContext) {session.open(context)?.let {invalidateVisit();read(it)}}
    fun retry(selection: QuickReplySelection) {session.retry(selection)?.let(::read)}
    private fun read(request: QuickReplyRequest) {
        state=session.state;val ticket=++readRevision;windowVisit++
        ownerScope.launch {
            val context=request.selection.context
            try {session.accept(repository.quickReplies(context.draft.context.business,context.channel),request)}
            catch(error: Exception) {
                if(error is CancellationException) {session.cancel(request);throw error}
                session.fail((error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE,request)
            } finally {
                state=session.state
                if(readRevision==ticket && state.selection==request.selection)windowVisit++
            }
        }
    }
    // Kotlin String equality already distinguishes raw code-unit edits.
    fun search(query: String,selection: QuickReplySelection) {val before=state.query;session.search(query,selection);state=session.state;if(state.query!=before)windowVisit++}
    fun close(selection: QuickReplySelection) {if(state.selection!=selection)return;session.close(selection);state=session.state;invalidateVisit()}
    fun resolve(choice: QuickReplyChoice)=session.resolve(choice)
    fun open(expected:QuickReplyEntryControl?) {if(expected!=null && entryControl==expected)open(expected.context)}
    fun retry(expected:QuickReplyControl?) {if(expected!=null && control==expected && !state.loading)retry(expected.selection)}
    fun search(query:String,input:QuickReplyInputControl?) {if(input!=null && inputControl==input)search(query,input.selection)}
    fun close(expected:QuickReplyControl?) {if(expected!=null && control==expected)close(expected.selection)}
    fun resolve(choice:QuickReplyChoice,expected:QuickReplyControl?):String?=if(expected!=null && control==expected)session.resolve(choice) else null
}
