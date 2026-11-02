package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientProfileRepository
import kz.zani.mobile.data.ClientWorkRepository
import kz.zani.mobile.data.ClientEditOriginProvider

// Parent-return snapshot is local UI state. Stale must never mean "close the parent".
enum class ClientWorkBack {CLOSED,NO_CHILD,STALE}
data class ClientWorkReturnControl(val read:ClientReadSelection?,val epoch:Int?,val edit:ClientEditControl?,val work:ClientWorkControl?,val editDialog:ClientEditConfirmation?,val merge:ClientMergePreviewControl?=null,val overlayVisit:Int=0)

data class ClientProfileState(val business: Int? = null, val id: Int? = null, val detail: ClientProfile? = null, val loading: Boolean = false, val problem: ReadProblem? = null,val scopeEpoch: Int? = null)
data class ClientMergeEntryControl(val read:ClientReadSelection,val epoch:Int,val visit:Int,val edit:ClientEditEntryControl?,val work:ClientWorkControl?)
class ClientProfileViewModel(private val repository: ClientProfileRepository, ownerScope: CoroutineScope? = null,private val editOriginSource: ClientEditOriginProvider? = null,mergeSource:SyntheticClientMergePreviewSource?=null) : ViewModel() {
    var state by mutableStateOf(ClientProfileState()); private set
    private val readScope = ownerScope ?: viewModelScope
    val merge=mergeSource?.let {ClientMergePreviewModel(it)}
    var localOverlayVisit by mutableStateOf(0);private set
    val edit=editOriginSource?.let {ClientEditModel()}
    val work = (repository as? ClientWorkRepository)?.let { ClientWorkModel(it, readScope) }
    private var revision = 0
    fun load(business: Int, id: Int, onContact: ((Int, ClientContact) -> Unit)? = null) = loadImpl(business, id, onContact, null,null)
    fun loadObserved(business: Int, id: Int, onFinished: () -> Unit) = loadImpl(business, id, null, onFinished,null)
    fun loadScoped(business: Int,id: Int,epoch: Int,onContact: ((Int,ClientContact)->Unit)?=null)=loadImpl(business,id,onContact,null,epoch)
    private fun loadImpl(business: Int, id: Int, onContact: ((Int, ClientContact) -> Unit)?, onFinished: (() -> Unit)?,epoch: Int?) {
        if(merge!=null) {merge.clear();localOverlayVisit++};work?.clear()
        val editContext=if(business>0 && id>0 && epoch!=null && epoch>0)ClientEditContext(business,id,epoch) else null
        edit?.begin(editContext)
        val ticket = ++revision; state = ClientProfileState(business, id, loading = true,scopeEpoch=epoch)
        if (business <= 0 || id <= 0) { state = state.copy(loading = false, problem = ReadProblem.INVALID_CONTEXT); onFinished?.invoke(); return }
        readScope.launch {
            try {
                val detail = repository.clientProfile(business, id)
                if (ticket != revision) return@launch
                if (!detail.validFor(business, id)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                val origin=if(editContext!=null)editOriginSource?.origin(detail) else null
                if(ticket!=revision)return@launch
                if(editContext!=null)edit?.receive(origin,editContext)
                state = state.copy(detail = detail, loading = false)
                work?.bind(detail, ClientReadSelection(business, id, ticket))
                onContact?.invoke(business, detail.client)
                onFinished?.invoke()
            } catch (error: Exception) {
                if (error is CancellationException) { if (ticket == revision) { state = state.copy(loading = false); onFinished?.invoke() }; throw error }
                if (ticket == revision) { state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE); onFinished?.invoke() }
            }
        }
    }
    val workReturnControl get()=ClientWorkReturnControl(readSelection,state.scopeEpoch,edit?.control,work?.presentation,edit?.confirmation,merge?.control,localOverlayVisit)
    fun backWork(expected:ClientWorkReturnControl?):ClientWorkBack {
        if(expected==null || workReturnControl!=expected)return ClientWorkBack.STALE
        if(work?.state?.selected==null)return ClientWorkBack.NO_CHILD
        return if(work?.back(presentation=expected.work)==true)ClientWorkBack.CLOSED else ClientWorkBack.STALE
    }
    fun backWork(): Boolean = work?.back() ?: false
    fun backEdit(expected:ClientWorkReturnControl?):Boolean {
        if(expected==null || workReturnControl!=expected)return false
        val editor=edit ?: return false
        expected.editDialog?.let {editor.dismiss(it);return true}
        val control=expected.edit ?: return false;editor.back(expected=control);return true
    }
    fun backEdit(): Boolean {val selection=edit?.state?.selection ?: return false;edit?.back(selection);return true}
    private val mergeContext:ClientMergePreviewContext? get() {
        val read=readSelection ?: return null;val epoch=state.scopeEpoch ?: return null
        return if(merge!=null && epoch>0 && state.detail!=null && !state.loading && state.problem==null)ClientMergePreviewContext(read.business,read.id,epoch,read.revision) else null
    }
    private val mergeOwnerAvailable get()=edit?.state?.selection==null && edit?.confirmation==null && work?.state?.selected==null
    val mergeEntry get()=mergeContext?.takeIf {merge?.context==null && mergeOwnerAvailable}?.let {ClientMergeEntryControl(readSelection!!,it.epoch,localOverlayVisit,edit?.entryControl,work?.presentation)}
    fun launchOpenMerge(expected:ClientMergeEntryControl?) {readScope.launch {openMerge(expected)}}
    suspend fun openMerge(expected:ClientMergeEntryControl?) {if(expected==null || mergeEntry!=expected)return;val context=mergeContext ?: return;localOverlayVisit++;merge?.open(context)}
    fun ownsMerge(expected:ClientMergePreviewControl?)=expected!=null && mergeContext==expected.context && mergeOwnerAvailable && merge?.control==expected
    fun chooseMerge(id:Int,expected:ClientMergePreviewControl?) {if(ownsMerge(expected))merge?.choose(id,expected)}
    fun launchPreviewMerge(expected:ClientMergePreviewControl?) {readScope.launch {previewMerge(expected)}}
    suspend fun previewMerge(expected:ClientMergePreviewControl?) {if(ownsMerge(expected))merge?.preview(expected)}
    fun launchRetryMerge(expected:ClientMergePreviewControl?) {readScope.launch {if(ownsMerge(expected) && merge?.loading==false)mergeContext?.let {merge?.open(it)}}}
    fun closeMerge(expected:ClientMergePreviewControl?):Boolean {if(!ownsMerge(expected))return false;merge?.clear();localOverlayVisit++;return true}
    fun backMerge(expected:ClientWorkReturnControl?):Boolean {if(expected==null || workReturnControl!=expected)return false;return closeMerge(expected.merge)}
    val readSelection:ClientReadSelection? get() {val b=state.business ?: return null;val id=state.id ?: return null;return if(b>0 && id>0)ClientReadSelection(b,id,revision) else null}
    fun retry(expected:ClientReadSelection?,epoch:Int?,onContact:((Int,ClientContact)->Unit)?=null) {if(expected==null || readSelection!=expected || state.scopeEpoch!=epoch || state.loading)return;loadImpl(expected.business,expected.id,onContact,null,epoch)}
    fun reconcileOwner(business:Int?,epoch:Int) {if(state.business!=business || state.scopeEpoch!=epoch)clear()}
    fun clear() { if(merge!=null) {merge.clear();localOverlayVisit++};edit?.pause();work?.clear(); revision++; state = ClientProfileState() }
}
