package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientRepository
import kz.zani.mobile.data.ClientSearchRepository

// Local UI correlation, never a server version/permission/wire key.
data class ClientDirectoryControl(val business:Int,val epoch:Int,val generation:Int,val selectedID:Int?)

data class ClientDirectoryListControl(val parent:ClientDirectoryControl)

data class ClientDirectoryState(
    val scopeEpoch: Int? = null, val searchRevision: Int = 0,
    val business: Int? = null, val items: List<ClientContact> = emptyList(),
    val query: String = "", val selectedID: Int? = null, val total: Int = 0,
    val loading: Boolean = false, val loaded: Boolean = false, val problem: ReadProblem? = null
) {
    val partial: Boolean get() = total > items.size
    val visible: List<ClientContact> get() {
        val needle = query.trim()
        return if (needle.isEmpty()) items else items.filter { client ->
            listOfNotNull(client.title, client.phone, client.email).any { it.contains(needle, ignoreCase = true) }
        }
    }
    val selected: ClientContact? get() = items.firstOrNull { it.id == selectedID }
    val showsEmpty: Boolean get() = loaded && !loading && problem == null && !partial && visible.isEmpty()
}

class ClientDirectoryViewModel(private val repository: ClientRepository,createSubmission:SyntheticClientCreatePort?=null,duplicateSource:SyntheticClientDuplicatePreviewSource?=null) : ViewModel() {
    var state by mutableStateOf(ClientDirectoryState()); private set
    val draft=ClientDraftModel(createSubmission,viewModelScope,duplicateSource)
    val serverSearch=(repository as? ClientSearchRepository)?.let {ClientSearchModel(it,viewModelScope)}
    private var searchRevision = 0
    private var revision = 0
    private var controlGeneration by mutableStateOf(0)
    val control:ClientDirectoryControl? get() {val b=state.business ?: return null;val e=state.scopeEpoch ?: return null;return if(b>0 && e>0)ClientDirectoryControl(b,e,controlGeneration,state.selectedID) else null}
    fun matches(expected:ClientDirectoryControl?)=expected!=null && control==expected
    val listControl get()=control?.takeIf {state.selectedID==null && draft.control==null && serverSearch?.state?.selection==null}?.let {ClientDirectoryListControl(it)}
    fun matchesList(expected:ClientDirectoryListControl?)=expected!=null && listControl==expected
    fun load(business: Int?, epoch: Int? = null) {
        serverSearch?.bind(if(business!=null && business>0 && epoch!=null && epoch>0)ClientSearchContext(business,epoch) else null)
        draft.bind(if (business != null && business > 0 && epoch != null && epoch > 0) ClientDraftContext(business,epoch) else null)
        ++searchRevision;++controlGeneration
        val ticket = ++revision
        val query = if (state.business == business && state.scopeEpoch == epoch) state.query else ""
        state = ClientDirectoryState(scopeEpoch = epoch, searchRevision = searchRevision, business = business, query = query, loading = business != null)
        if (business == null) return
        if (business <= 0) { state = state.copy(loading = false, problem = ReadProblem.INVALID_CONTEXT); return }
        viewModelScope.launch {
            try {
                val page = repository.clients(business)
                if (ticket != revision) return@launch
                if (page.business != business || page.total < page.items.size || page.items.any { it.id <= 0 } ||
                    page.items.map { it.id }.distinct().size != page.items.size) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(items = page.items, total = page.total, loading = false, loaded = true)
            } catch (error: Exception) {
                if (error is CancellationException) { if (ticket == revision) state = state.copy(loading = false); throw error }
                if (ticket == revision) {state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE);if(state.problem==ReadProblem.DENIED)serverSearch?.bind(null)}
            }
        }
    }
    fun search(query: String) { state = state.copy(query = query) }
    // Local root owner invalidation without GET or auth/permission changes.
    fun reconcileOwner(business:Int?,epoch:Int) {
        if(state.business==business && state.scopeEpoch==epoch)return
        ++revision;++controlGeneration;serverSearch?.bind(null);draft.bind(null);state=ClientDirectoryState(searchRevision=++searchRevision)
    }
    fun open(id: Int) { if (state.items.any { it.id == id }) { draft.state.selection?.let(draft::close); state = state.copy(selectedID = id);++controlGeneration } }
    fun back() { serverSearch?.state?.selection?.let {serverSearch?.close(it)}; draft.state.selection?.let(draft::close); state = state.copy(selectedID = null);++controlGeneration }
    fun refreshContact(business: Int, contact: ClientContact) {
        if (state.business == business && state.selectedID == contact.id) state = state.copy(searchRevision = ++searchRevision, items = state.items.map { if (it.id == contact.id) contact else it })
    }
    fun search(value:String,expected:ClientDirectoryControl?) {if(matches(expected) && !state.loading && state.selectedID==null)search(value)}
    fun open(id:Int,expected:ClientDirectoryControl?):Boolean {
        if(!matches(expected) || !state.loaded || state.loading || state.problem!=null || state.visible.none {it.id==id})return false
        open(id);return true
    }
    fun back(expected:ClientDirectoryControl?):Boolean {if(!matches(expected))return false;back();return true}
    fun retry(expected:ClientDirectoryControl?) {if(!matches(expected) || state.loading || expected==null)return;load(expected.business,expected.epoch)}
    fun refreshContact(business:Int,contact:ClientContact,expected:ClientDirectoryControl?) {if(matches(expected) && !state.loading)refreshContact(business,contact)}
    fun openDraft(expected:ClientDirectoryControl?):Boolean {
        if(!matches(expected) || !state.loaded || state.loading || state.problem!=null || expected==null)return false
        back();draft.open(ClientDraftContext(expected.business,expected.epoch));return draft.state.selection!=null
    }
    fun openSearch(expected:ClientDirectoryControl?):Boolean {
        if(!matches(expected) || state.loading || expected==null || serverSearch==null)return false
        back();serverSearch.open(ClientSearchContext(expected.business,expected.epoch));return serverSearch.state.selection!=null
    }

    // UI list-only controls; retain trusted explicit switching APIs unchanged.
    fun searchList(value:String,list:ClientDirectoryListControl?) {if(list!=null && matchesList(list))search(value,list.parent)}
    fun openList(id:Int,list:ClientDirectoryListControl?):Boolean=if(list!=null && matchesList(list))open(id,list.parent) else false
    fun retryList(list:ClientDirectoryListControl?) {if(list!=null && matchesList(list))retry(list.parent)}
    fun openDraftFromList(expected:ClientDraftEntryControl?,list:ClientDirectoryListControl?):Boolean {
        if(expected==null || list==null || !matchesList(list) || draft.entryControl!=expected || expected.context.business!=list.parent.business || expected.context.epoch!=list.parent.epoch)return false
        return openDraft(list.parent)
    }
    fun openSearchFromList(list:ClientDirectoryListControl?):Boolean=if(list!=null && matchesList(list))openSearch(list.parent) else false
}
