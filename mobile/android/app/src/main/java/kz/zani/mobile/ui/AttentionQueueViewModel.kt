package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AttentionRepository

// Composite source identity plus local owner/visit stamps, not a wire version or grant.
data class AttentionControl(val business:Int,val epoch:Int,val revision:Int,val detailRevision:Int,val identity:AttentionIdentity?)

data class AttentionQueueState(val business: Int? = null, val items: List<AttentionItem> = emptyList(), val limit: Int = 0,
    val loaded: Boolean = false, val loading: Boolean = false, val problem: ReadProblem? = null, val query: String = "",
    val selectedID: AttentionIdentity? = null, val detail: AttentionDetail? = null, val detailLoading: Boolean = false, val detailProblem: ReadProblem? = null,val scopeEpoch:Int?=null) {
    val selected: AttentionItem? get() = items.firstOrNull { it.identity == selectedID }
    val windowCapped: Boolean get() = loaded && items.size == limit
    val visible: List<AttentionItem> get() = items.filter { query.isBlank() || it.entity.title?.contains(query.trim(), ignoreCase = true) == true }
    val showsEmpty: Boolean get() = loaded && !loading && problem == null && !windowCapped && visible.isEmpty()
}
class AttentionQueueViewModel(private val repository: AttentionRepository) : ViewModel() {
    var state by mutableStateOf(AttentionQueueState()); private set
    private var revision = 0
    private var detailRevision = 0
    val control:AttentionControl? get() {val business=state.business?.takeIf {it>0} ?: return null;val epoch=state.scopeEpoch?.takeIf {it>0} ?: return null;return AttentionControl(business,epoch,revision,detailRevision,state.selectedID)}
    fun matches(expected:AttentionControl?)=expected!=null && control==expected
    fun load(business: Int?,epoch:Int?=null) {
        val ticket = ++revision; ++detailRevision
        state = AttentionQueueState(business = business,scopeEpoch=epoch, query = if (state.business == business && state.scopeEpoch==epoch) state.query else "", loading = business != null)
        if (business == null) return
        if (business <= 0 || (epoch!=null && epoch<=0)) { state = state.copy(loading = false, problem = ReadProblem.INVALID_CONTEXT); return }
        viewModelScope.launch {
            try {
                val page = repository.actions(business)
                if (ticket != revision) return@launch
                if (!page.validFor(business)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(items = page.items, limit = page.limit, loaded = true, loading = false)
            } catch (error: Exception) {
                if (error is CancellationException) { if (ticket == revision) state = state.copy(loading = false); throw error }
                if (ticket == revision) state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    fun search(query: String) { state = state.copy(query = query) }
    fun open(identity: AttentionIdentity) {
        val item = state.items.firstOrNull { it.identity == identity } ?: return
        val target = item.readTarget ?: return; val business = state.business ?: return
        val ticket = ++detailRevision; val scope = revision
        state = state.copy(selectedID = identity, detail = null, detailLoading = true, detailProblem = null)
        viewModelScope.launch {
            try {
                val response: AttentionDetail = when (target.kind) {
                    AttentionKind.TASK -> AttentionDetail.TaskRead(repository.taskDetails(business, target.id))
                    AttentionKind.CONVERSATION -> AttentionDetail.ThreadRead(repository.thread(business, target.id))
                    AttentionKind.APPOINTMENT -> AttentionDetail.AppointmentRead(repository.appointment(business, target.id))
                }
                if (ticket != detailRevision || scope != revision) return@launch
                if (!response.validFor(business, target)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(detail = response, detailLoading = false, items = state.items.map { row -> if (row.identity == identity) row.copy(entity = row.entity.copy(title = response.title)) else row })
            } catch (error: Exception) {
                if (error is CancellationException) { if (ticket == detailRevision && scope == revision) back(); throw error }
                if (ticket == detailRevision && scope == revision) state = state.copy(detailLoading = false, detailProblem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    fun search(value:String,expected:AttentionControl?) {if(matches(expected) && !state.loading && state.selectedID==null)search(value)}
    fun retryList(expected:AttentionControl?) {if(expected!=null && matches(expected) && !state.loading && state.selectedID==null)load(expected.business,expected.epoch)}
    fun open(identity:AttentionIdentity,expected:AttentionControl?) {if(matches(expected) && state.loaded && !state.loading && state.problem==null && state.selectedID==null && state.visible.any {it.identity==identity})open(identity)}
    fun retryDetail(expected:AttentionControl?) {val id=state.selectedID;if(matches(expected) && !state.detailLoading && id!=null)open(id)}
    fun back(expected:AttentionControl?) {if(matches(expected) && state.selectedID!=null)back()}
    fun reconcileOwner(business:Int?,epoch:Int) {if(state.business!=business || state.scopeEpoch!=epoch)clear()}
    fun clear() {++revision;++detailRevision;state=AttentionQueueState()}
    fun back() { ++detailRevision; state = state.copy(selectedID = null, detail = null, detailLoading = false, detailProblem = null) }
}
