package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kz.zani.mobile.core.*

// Local UI visits, never source versions or command grants.
data class ClientEditEntryControl(val context:ClientEditContext,val visit:Int)
data class ClientEditControl(val selection:ClientEditSelection,val visit:Int)
data class ClientEditInputControl(val control:ClientEditControl)
data class ClientEditConfirmation(val id:Int,val entry:ClientEditEntryControl?,val control:ClientEditControl?,val contentRevision:Int)
class ClientEditModel {
    private val session=ClientEditSession()
    var state by mutableStateOf(session.state);private set
    private var entryVisit by mutableStateOf(0)
    private var viewVisit by mutableStateOf(0)
    var confirmation by mutableStateOf<ClientEditConfirmation?>(null);private set
    private var contentRevision=0;private var dialogRevision=0
    val hasStoredChanges get()=session.hasStoredChanges
    val entryControl get()=state.context?.takeIf {state.selection==null}?.let {ClientEditEntryControl(it,entryVisit)}
    val control get()=state.selection?.let {ClientEditControl(it,viewVisit)}
    val inputControl get()=control?.takeIf {state.phase==ClientDraftPhase.EDITING}?.let {ClientEditInputControl(it)}
    private fun invalidate() {entryVisit++;viewVisit++;confirmation=null}
    fun begin(context: ClientEditContext?) {session.begin(context);state=session.state;invalidate()}
    fun receive(origin: ClientEditOrigin?,context: ClientEditContext) {if(state.context!=context)return;session.receive(origin,context);state=session.state;invalidate()}
    fun pause() {session.pause();state=session.state;invalidate()}
    // Raw trusted local APIs retained; UI uses captured controls below.
    fun open(context: ClientEditContext) {if(session.open(context)) {state=session.state;invalidate()}}
    fun update(field: ClientDraftField,value: String,selection: ClientEditSelection) {
        val before=state.values;session.update(field,value,selection);state=session.state
        if(state.values!=before) {contentRevision++;confirmation=null}
    }
    fun prepare(selection: ClientEditSelection) {val accepted=session.prepare(selection);state=session.state;if(accepted) {viewVisit++;confirmation=null}}
    fun back(selection: ClientEditSelection) {if(state.selection!=selection)return;session.back(selection);state=session.state;invalidate()}
    fun close(selection: ClientEditSelection) {if(state.selection!=selection)return;session.close(selection);state=session.state;invalidate()}
    fun cancel(selection: ClientEditSelection) {if(state.selection!=selection)return;session.cancel(selection);state=session.state;contentRevision++;invalidate()}
    fun discardStored(context: ClientEditContext) {if(state.context!=context)return;session.discardStored(context);state=session.state;contentRevision++;invalidate()}
    fun open(expected:ClientEditEntryControl?) {if(expected!=null && entryControl==expected)open(expected.context)}
    fun update(field:ClientDraftField,value:String,input:ClientEditInputControl?) {if(input!=null && inputControl==input)update(field,value,input.control.selection)}
    fun prepare(expected:ClientEditControl?) {if(expected!=null && control==expected)prepare(expected.selection)}
    fun back(expected:ClientEditControl?) {if(expected!=null && control==expected)back(expected.selection)}
    fun close(expected:ClientEditControl?) {if(expected!=null && control==expected)close(expected.selection)}
    fun askCancel(expected:ClientEditControl?) {
        if(expected==null || control!=expected || !state.available || state.origin==null)return
        confirmation=ClientEditConfirmation(++dialogRevision,null,expected,contentRevision)
    }
    fun askDiscard(expected:ClientEditEntryControl?) {
        if(expected==null || entryControl!=expected || !state.needsReset || !hasStoredChanges)return
        confirmation=ClientEditConfirmation(++dialogRevision,expected,null,contentRevision)
    }
    fun dismiss(expected:ClientEditConfirmation) {if(confirmation==expected)confirmation=null}
    fun confirm(expected:ClientEditConfirmation) {
        if(confirmation!=expected || expected.contentRevision!=contentRevision)return
        val editor=expected.control;val entry=expected.entry
        if(editor!=null && control==editor)cancel(editor.selection)
        else if(entry!=null && entryControl==entry && state.needsReset && hasStoredChanges)discardStored(entry.context)
    }
}
