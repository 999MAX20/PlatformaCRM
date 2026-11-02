package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.InboxClientRepository

// Local presentation generation only, not a wire/session/access DTO.
data class InboxReadSelection(val business: Int,val id: Int,val revision: Int)
data class InboxClientPresentation(val request:InboxReadSelection,val selectedID:Int?,val generation:Int)
data class InboxClientEntryControl(val presentation:InboxClientPresentation)
data class InboxClientControl(val presentation:InboxClientPresentation,val profile:ClientReadSelection?,val loading:Boolean,val profileLoading:Boolean)
data class InboxClientReturnControl(val inspector:InboxClientControl,val profile:ClientWorkReturnControl)
data class InboxClientState(val request: InboxReadSelection? = null,val parent: InboxThread? = null,val selectedID: Int? = null,val loading: Boolean = false)
class InboxClientModel(private val repository: InboxClientRepository,private val scope: CoroutineScope) {
    var state by mutableStateOf(InboxClientState()); private set
    val profile = ClientProfileViewModel(repository,scope)
    private var revision by mutableStateOf(0)
    val presentation:InboxClientPresentation? get()=state.request?.let {InboxClientPresentation(it,state.selectedID,revision)}
    val entryControl get()=presentation?.takeIf {state.selectedID==null && !state.loading && state.parent?.clientReferenceID!=null}?.let {InboxClientEntryControl(it)}
    val control get()=presentation?.let {InboxClientControl(it,profile.readSelection,state.loading,profile.state.loading)}
    val returnControl get()=control?.let {InboxClientReturnControl(it,profile.workReturnControl)}
    private var onThread: ((InboxThread?,ReadProblem?) -> Unit)? = null
    fun bind(thread: InboxThread,request: InboxReadSelection,onThread: (InboxThread?,ReadProblem?) -> Unit) {
        clear()
        if (request.revision <= 0 || !thread.validFor(request.business,request.id)) return
        state = InboxClientState(request,thread); this.onThread = onThread
    }
    fun open(expected: InboxReadSelection? = null) {
        if (expected != null && expected != state.request) return
        val request = state.request ?: return
        val id = state.parent?.clientReferenceID ?: return
        back(); val ticket = revision; val callback=onThread; state = state.copy(selectedID=id,loading=true)
        scope.launch {
            try {
                val fresh = repository.thread(request.business,request.id)
                if (!current(request,id,ticket)) return@launch
                if (!fresh.validFor(request.business,request.id)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(parent=fresh)
                if(!current(request,id,ticket))return@launch
                callback?.invoke(fresh,null)
                if(!current(request,id,ticket))return@launch
                if (fresh.clientReferenceID != id) { back(); return@launch }
            } catch (error: Exception) {
                if (current(request,id,ticket)) {
                    if (error !is CancellationException) {
                        callback?.invoke(null,(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
                        if(!current(request,id,ticket))return@launch
                        state = state.copy(parent=null)
                    }
                    if(!current(request,id,ticket))return@launch
                    back()
                }
                if (error is CancellationException) throw error
                return@launch
            }
            if(!current(request,id,ticket))return@launch
            profile.loadObserved(request.business,id) {
                if (current(request,id,ticket)) {
                    state = state.copy(loading=false)
                    if (profile.state.detail == null && profile.state.problem == null) back()
                }
            }
        }
    }
    private fun current(request: InboxReadSelection,id: Int,ticket: Int) = state.request == request && state.selectedID == id && revision == ticket
    fun back(expected: InboxReadSelection? = null): Boolean {
        if (expected != null && expected != state.request) return false
        val hadChild = state.selectedID != null
        ++revision; profile.clear(); state = state.copy(selectedID=null,loading=false); return hadChild
    }
    fun open(presentation:InboxClientPresentation?) {if(presentation!=null && this.presentation==presentation)open(presentation.request)}
    fun back(presentation:InboxClientPresentation?):Boolean {if(presentation==null || this.presentation!=presentation)return false;return back(presentation.request)}
    fun clear() { back(); state = InboxClientState(); onThread = null }
    fun openEntry(expected:InboxClientEntryControl?) {if(expected!=null && entryControl==expected)open(presentation=expected.presentation)}
    fun retry(expected:InboxClientControl?) {
        if(expected==null || control!=expected || state.selectedID==null || state.loading || profile.state.loading || profile.work?.state?.selected!=null || profile.edit?.control!=null)return
        open(presentation=expected.presentation)
    }
    fun closeInspector(expected:InboxClientReturnControl?):Boolean {
        if(expected==null || returnControl!=expected || state.selectedID==null || expected.profile.work?.target!=null || expected.profile.edit!=null || expected.profile.editDialog!=null)return false
        return back(presentation=expected.inspector.presentation)
    }
}
