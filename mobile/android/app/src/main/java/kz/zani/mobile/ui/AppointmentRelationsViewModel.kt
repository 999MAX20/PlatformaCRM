package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.cancel
import kz.zani.mobile.core.*
import kz.zani.mobile.data.AppointmentRelatedRepository
import kz.zani.mobile.data.AppointmentReferenceRepository
import kz.zani.mobile.data.AppointmentSlotRepository

// Local related-read visit, not parent/server version or access authority.
data class AppointmentRelationControl(val request:DetailSelection,val generation:Int,val target:AppointmentRelatedTarget?)

data class AppointmentRelationsState(val request: DetailSelection? = null, val parent: AppointmentDetail? = null, val tasks: List<WorkTask>? = null,
    val selected: AppointmentRelatedTarget? = null, val task: TaskDetails? = null, val reference:AppointmentReferenceDetail?=null, val loading: Boolean = false, val problem: ReadProblem? = null)
class AppointmentRelationsViewModel(private val repository: AppointmentRelatedRepository,private val references:AppointmentReferenceRepository?=null,slots:AppointmentSlotRepository?=null) : ViewModel() {
    val profile = ClientProfileViewModel(repository)
    val slotReads=AppointmentSlotReadViewModel(slots,references)
    var state by mutableStateOf(AppointmentRelationsState()); private set
    private var revision by mutableStateOf(0)
    fun bind(parent: AppointmentDetail, request: DetailSelection) {
        clear()
        if (request.id <= 0 || request.scope.business.id <= 0 || parent.business != request.scope.business.id || parent.appointment.id != request.id) return
        state = AppointmentRelationsState(request = request, parent = parent, tasks = parent.providedTasks)
    }
    fun openClient(expected: DetailSelection? = null) {
        if (expected != null && expected != state.request) return
        val request = state.request ?: return; val id = state.parent?.linkedClientID ?: return
        back(); state = state.copy(selected = AppointmentRelatedTarget.Client(id))
        profile.load(request.scope.business.id,id)
    }
    fun openTask(id: Int, expected: DetailSelection? = null) {
        if (expected != null && expected != state.request) return
        val request = state.request ?: return; val parent = state.parent ?: return
        if (state.tasks?.none { it.id == id } != false) return
        back(); val ticket = revision; state = state.copy(selected = AppointmentRelatedTarget.Task(id), loading = true)
        viewModelScope.launch {
            try {
                val result = repository.taskDetails(request.scope.business.id,id)
                if (revision != ticket || state.request != request) return@launch
                if (!result.validFor(request.scope.business.id,id) || result.appointmentID != parent.appointment.id) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state = state.copy(task = result, loading = false, tasks = state.tasks?.map { if (it.id == id) result.task else it })
            } catch (error: Exception) {
                if (error is CancellationException) { if (revision == ticket && state.request == request) back(); throw error }
                if (revision == ticket && state.request == request) state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    fun referenceAvailable(kind:AppointmentReferenceKind)=references!=null && (state.request?.revision ?: 0)>0 && (state.request?.scope?.revision ?: 0)>0 && state.parent?.referenceID(kind)!=null
    fun openReference(kind:AppointmentReferenceKind,presentation:AppointmentRelationControl?) {
        if(presentation==null || !matches(presentation) || state.selected!=null || !referenceAvailable(kind))return
        loadReference(kind,presentation.request)
    }
    private fun loadReference(kind:AppointmentReferenceKind,expected:DetailSelection) {
        val request=state.request ?: return;val id=state.parent?.referenceID(kind) ?: return;val references=references ?: return
        if(request!=expected)return
        back();val ticket=revision;state=state.copy(selected=if(kind==AppointmentReferenceKind.SERVICE)AppointmentRelatedTarget.Service(id) else AppointmentRelatedTarget.Resource(id),loading=true)
        viewModelScope.launch {
            try {
                val detail=references.reference(kind,request.scope.business.id,id)
                if(revision!=ticket || state.request!=request)return@launch
                if(!detail.validFor(request.scope.business.id,id))throw ReadException(ReadProblem.INVALID_PAYLOAD)
                state=state.copy(reference=detail,loading=false)
                if(kind==AppointmentReferenceKind.SERVICE)slotReads.bind(detail,request,state.parent?.referenceID(AppointmentReferenceKind.RESOURCE))
            } catch(error:Exception) {
                if(error is CancellationException){if(revision==ticket && state.request==request)back();throw error}
                if(revision==ticket && state.request==request)state=state.copy(loading=false,problem=(error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    val presentation:AppointmentRelationControl? get()=state.request?.let {AppointmentRelationControl(it,revision,state.selected)}
    fun matches(expected:AppointmentRelationControl?)=expected!=null && presentation==expected
    fun openClient(presentation:AppointmentRelationControl?) {if(presentation!=null && matches(presentation) && state.selected==null)openClient(presentation.request)}
    fun openTask(id:Int,presentation:AppointmentRelationControl?) {if(presentation!=null && matches(presentation) && state.selected==null)openTask(id,presentation.request)}
    fun retry(presentation:AppointmentRelationControl?) {if(presentation==null || !matches(presentation) || state.loading || profile.state.loading)return;when(val target=state.selected) {is AppointmentRelatedTarget.Client->openClient(presentation.request);is AppointmentRelatedTarget.Task->openTask(target.id,presentation.request);is AppointmentRelatedTarget.Service->loadReference(AppointmentReferenceKind.SERVICE,presentation.request);is AppointmentRelatedTarget.Resource->loadReference(AppointmentReferenceKind.RESOURCE,presentation.request);null->Unit}}
    fun back(presentation:AppointmentRelationControl?) {if(matches(presentation) && state.selected!=null)back()}
    fun back() { slotReads.clear();++revision; profile.clear(); state = state.copy(selected = null, task = null, reference=null, loading = false, problem = null) }
    fun clear() { back(); state = AppointmentRelationsState() }
    override fun onCleared() { clear(); slotReads.viewModelScope.cancel();profile.viewModelScope.cancel(); super.onCleared() }
}
