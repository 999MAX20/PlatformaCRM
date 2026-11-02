package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.NotificationRepository

// Local owner/visit identity only; no wire/version/grant fields.
data class NotificationControl(val business:Int,val epoch:Int,val generation:Int,val notification:Int?,val appointment:Int?)

data class NotificationRouteControl(val parent:NotificationControl,val generation:Int,val reviewing:Boolean)

data class NotificationCenterState(val scopeEpoch:Int?=null,val business: Int? = null, val items: List<CRMNotification> = emptyList(), val total: Int = 0,
    val query: String = "", val category: String? = null, val unreadOnly: Boolean = false, val loaded: Boolean = false, val loading: Boolean = false, val problem: ReadProblem? = null,
    val selectedID: Int? = null, val targetActive: Boolean = false, val target: AppointmentDetail? = null, val targetLoading: Boolean = false, val targetProblem: ReadProblem? = null) {
    val partial: Boolean get() = total > items.size
    val categories: List<String> get() = (items.mapNotNull { it.category } + listOfNotNull(category)).distinct()
    val selected: CRMNotification? get() = items.firstOrNull { it.id == selectedID }
    val visible: List<CRMNotification> get() = items.filter { n -> (!unreadOnly || n.unread) && (category == null || n.category == category) &&
        (query.isBlank() || n.text?.contains(query.trim(), ignoreCase = true) == true) }
    val showsEmpty: Boolean get() = loaded && !loading && problem == null && !partial && visible.isEmpty()
}
class NotificationCenterViewModel(private val repository:NotificationRepository,markReadSubmission:SyntheticNotificationMarkReadPort?=null,markUnreadSubmission:SyntheticNotificationMarkUnreadPort?=null) : ViewModel() {
    val markRead=NotificationMarkReadModel(markReadSubmission,viewModelScope)
    val markUnread=NotificationMarkUnreadModel(markUnreadSubmission,viewModelScope)
    init {
        markRead.peerBlocked={markUnread.blocks(it)}
        markUnread.peerBlocked={markRead.blocks(it)}
        markRead.onDispatch={markUnread.invalidatePreparedReview()}
        markUnread.onDispatch={markRead.invalidatePreparedReview()}
    }
    var state by mutableStateOf(NotificationCenterState()); private set
    private var controlGeneration by mutableStateOf(0)
    val control:NotificationControl? get() {val b=state.business ?: return null;val e=state.scopeEpoch ?: return null;return if(b>0 && e>0)NotificationControl(b,e,controlGeneration,state.selectedID,state.selected?.appointmentTarget) else null}
    fun matches(expected:NotificationControl?)=expected!=null && control==expected
    var routeEditorActive by mutableStateOf(false); private set
    var routeInput by mutableStateOf(""); private set
    var routeReviewing by mutableStateOf(false); private set
    private var routeGeneration by mutableStateOf(0)
    val routeControl:NotificationRouteControl? get() {
        val parent=control ?: return null
        if(!routeEditorActive || state.selected==null || state.targetActive || !state.loaded || state.loading || state.problem!=null)return null
        return NotificationRouteControl(parent,routeGeneration,routeReviewing)
    }
    val routeCandidate:RelativeAppointmentCandidate? get()=if(routeReviewing)RelativeAppointmentCandidate.parse(routeInput) else null
    val routeCorroborated:Boolean get() {val source=state.selected ?: return false;return routeCandidate?.corroboratedTarget(source)!=null}
    fun matchesRoute(expected:NotificationRouteControl?)=expected!=null && routeControl==expected
    fun beginRoute(expected:NotificationControl?) {
        if(!matches(expected) || !state.loaded || state.loading || state.problem!=null || state.selected==null || state.targetActive || routeEditorActive)return
        ++controlGeneration;++routeGeneration;routeEditorActive=true;routeReviewing=false;syncMarkRead()
    }
    fun editRoute(raw:String,expected:NotificationRouteControl?) {if(matchesRoute(expected) && !routeReviewing)routeInput=raw}
    fun reviewRoute(expected:NotificationRouteControl?) {if(matchesRoute(expected) && !routeReviewing){++routeGeneration;routeReviewing=true}}
    fun backRoute(expected:NotificationRouteControl?) {
        if(!matchesRoute(expected))return
        ++routeGeneration
        if(routeReviewing)routeReviewing=false else {++controlGeneration;routeEditorActive=false;syncMarkRead()}
    }
    private fun resetRoute() {++routeGeneration;routeEditorActive=false;routeReviewing=false;routeInput=""}
    private var revision = 0
    private var targetRevision = 0
    fun load(business: Int?,epoch:Int?=null) {
        resetRoute();markRead.bind(null);markUnread.bind(null);val ticket = ++revision; ++targetRevision;++controlGeneration
        state = NotificationCenterState(scopeEpoch=epoch,business = business, query = if (state.business == business && state.scopeEpoch==epoch) state.query else "",
            category = state.category.takeIf { state.business == business && state.scopeEpoch==epoch }, unreadOnly = state.business == business && state.scopeEpoch==epoch && state.unreadOnly, loading = business != null)
        if (business == null) return
        if (business <= 0) { state = state.copy(loading = false, problem = ReadProblem.INVALID_CONTEXT); return }
        viewModelScope.launch {
            try {
                val page = repository.notifications(business)
                if (ticket != revision) return@launch
                if (!page.validFor(business)) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(items = page.items, total = page.total, loaded = true, loading = false)
            } catch (error: Exception) {
                if (error is CancellationException) { if (ticket == revision) state = state.copy(loading = false); throw error }
                if (ticket == revision) state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    fun search(query: String) { state = state.copy(query = query) }
    fun filter(category: String?) { state = state.copy(category = category) }
    fun unreadOnly(enabled: Boolean) { state = state.copy(unreadOnly = enabled) }
    fun open(id: Int) { if (state.items.any { it.id == id }) { close(); state = state.copy(selectedID = id);syncMarkRead() } }
    fun openTarget() {
        if(routeEditorActive)return
        val notification = state.selected ?: return
        val id = notification.appointmentTarget ?: return
        val business = state.business ?: return
        ++controlGeneration;val scope = revision; val ticket = ++targetRevision
        state = state.copy(targetActive = true, target = null, targetLoading = true, targetProblem = null);syncMarkRead()
        viewModelScope.launch {
            try {
                val target = repository.appointment(business, id)
                if (scope != revision || ticket != targetRevision) return@launch
                val valid = runCatching { target.business == business && target.appointment.id == id && target.appointment.end > target.appointment.start }.getOrDefault(false)
                if (!valid) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(target = target, targetLoading = false)
            } catch (error: Exception) {
                if (error is CancellationException) { if (scope == revision && ticket == targetRevision) backTarget(); throw error }
                if (scope == revision && ticket == targetRevision) state = state.copy(targetLoading = false, targetProblem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    fun backTarget() { ++controlGeneration;++targetRevision; state = state.copy(targetActive = false, target = null, targetLoading = false, targetProblem = null);syncMarkRead() }
    fun close() { resetRoute();backTarget(); state = state.copy(selectedID = null);syncMarkRead() }
    fun back() { if(routeEditorActive)backRoute(routeControl) else if (state.targetActive) backTarget() else close() }
    private fun syncMarkRead() {
        val control=control;val selected=state.selected
        markRead.bind(if(!routeEditorActive && !state.targetActive && state.loaded && !state.loading && state.problem==null && control!=null && selected!=null)NotificationMarkReadSource(NotificationMarkReadContext(control.business,selected.id,control.epoch),control.generation,selected) else null)
        markUnread.bind(if(!routeEditorActive && !state.targetActive && state.loaded && !state.loading && state.problem==null && control!=null && selected!=null)NotificationMarkUnreadSource(NotificationMarkUnreadContext(control.business,selected.id,control.epoch),control.generation,selected) else null)
    }
    fun clear() {resetRoute();++revision;++targetRevision;++controlGeneration;state=NotificationCenterState();markRead.bind(null);markUnread.bind(null)}
    fun reconcileOwner(business:Int?,epoch:Int) {if(state.business!=business || state.scopeEpoch!=epoch)clear()}
    fun search(value:String,expected:NotificationControl?) {if(matches(expected) && !state.loading && state.selectedID==null)search(value)}
    fun filterCategory(value:String?,previous:String?,expected:NotificationControl?) {if(matches(expected) && !state.loading && state.selectedID==null && state.category==previous)filter(value)}
    fun filterUnread(value:Boolean,previous:Boolean,expected:NotificationControl?) {if(matches(expected) && !state.loading && state.selectedID==null && state.unreadOnly==previous)unreadOnly(value)}
    fun open(id:Int,expected:NotificationControl?) {if(matches(expected) && state.loaded && !state.loading && state.problem==null && state.selectedID==null && state.visible.any {it.id==id})open(id)}
    fun retryList(expected:NotificationControl?) {if(expected!=null && matches(expected) && !state.loading && state.selectedID==null)load(expected.business,expected.epoch)}
    fun openTarget(expected:NotificationControl?) {if(matches(expected) && !state.targetLoading && state.loaded && state.problem==null)openTarget()}
    fun close(expected:NotificationControl?) {if(matches(expected))close()}
    fun backTarget(expected:NotificationControl?) {if(matches(expected) && state.targetActive)backTarget()}
    fun back(expected:NotificationControl?) {if(matches(expected))back()}

}
