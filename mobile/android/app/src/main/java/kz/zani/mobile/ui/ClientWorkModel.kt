package kz.zani.mobile.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*
import kz.zani.mobile.data.ClientWorkRepository

// Local child visit identity, never a server version/permission or durable token.
data class ClientWorkControl(val selection:ClientReadSelection,val generation:Int,val target:ClientWorkTarget?)

data class ClientWorkState(val selection: ClientReadSelection? = null, val parent: ClientProfile? = null,
    val tasks: List<WorkTask>? = null, val conversations: List<InboxConversation>? = null, val appointments: List<Appointment>? = null,
    val selected: ClientWorkTarget? = null, val detail: AttentionDetail? = null, val loading: Boolean = false, val problem: ReadProblem? = null)

// Uses the owning profile's scope; no independent lifecycle or persistent cache.
class ClientWorkModel(private val repository: ClientWorkRepository, private val scope: CoroutineScope) {
    var state by mutableStateOf(ClientWorkState()); private set
    private var revision by mutableStateOf(0)
    fun bind(profile: ClientProfile, selection: ClientReadSelection) {
        clear()
        if (selection.revision <= 0 || !profile.validFor(selection.business, selection.id)) return
        state = ClientWorkState(selection, profile, profile.providedTasks, profile.providedConversations, profile.providedAppointments)
    }
    fun open(target: ClientWorkTarget, expected: ClientReadSelection? = null) {
        if (expected != null && expected != state.selection) return
        val request = state.selection ?: return
        val provided = when (target) {
            is ClientWorkTarget.Task -> state.tasks?.any { it.id == target.id } == true
            is ClientWorkTarget.Conversation -> state.conversations?.any { it.id == target.id } == true
            is ClientWorkTarget.Appointment -> state.appointments?.any { it.id == target.id } == true
        }
        if (!provided) return
        back(); val ticket = revision; state = state.copy(selected = target, loading = true)
        scope.launch {
            try {
                val result = when (target) {
                    is ClientWorkTarget.Task -> repository.taskDetails(request.business, target.id).let {
                        if (!it.validFor(request.business, target.id) || it.task.clientID != request.id) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.TaskRead(it)
                    }
                    is ClientWorkTarget.Conversation -> repository.thread(request.business, target.id).let {
                        if (!it.validFor(request.business, target.id) || it.clientReferenceID != request.id) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.ThreadRead(it)
                    }
                    is ClientWorkTarget.Appointment -> repository.appointment(request.business, target.id).let {
                        if (it.business != request.business || it.appointment.id != target.id || it.linkedClientID != request.id) throw ReadException(ReadProblem.INVALID_PAYLOAD)
                        AttentionDetail.AppointmentRead(it)
                    }
                }
                if (!current(request,target,ticket)) return@launch
                state = when (result) {
                    is AttentionDetail.TaskRead -> state.copy(tasks = state.tasks?.map { if (it.id == result.value.task.id) result.value.task else it })
                    is AttentionDetail.ThreadRead -> state.copy(conversations = state.conversations?.map { if (it.id == result.value.conversation.id) result.value.conversation else it })
                    is AttentionDetail.AppointmentRead -> state.copy(appointments = state.appointments?.map { if (it.id == result.value.appointment.id) result.value.appointment else it })
                }.copy(detail = result, loading = false)
            } catch (error: Exception) {
                if (error is CancellationException) { if (current(request,target,ticket)) back(); throw error }
                if (current(request,target,ticket)) state = state.copy(loading = false, problem = (error as? ReadException)?.problem ?: ReadProblem.UNAVAILABLE)
            }
        }
    }
    private fun current(request: ClientReadSelection, target: ClientWorkTarget, ticket: Int) = revision == ticket && state.selection == request && state.selected == target
    fun back(expected: ClientReadSelection? = null): Boolean {
        if (expected != null && expected != state.selection) return false
        val hadChild = state.selected != null
        ++revision; state = state.copy(selected = null, detail = null, loading = false, problem = null)
        return hadChild
    }
    val presentation:ClientWorkControl? get()=state.selection?.let {ClientWorkControl(it,revision,state.selected)}
    fun matches(expected:ClientWorkControl?)=expected!=null && presentation==expected
    fun open(target:ClientWorkTarget,presentation:ClientWorkControl?) {if(presentation!=null && matches(presentation) && state.selected==null && !state.loading)open(target,presentation.selection)}
    fun retry(presentation:ClientWorkControl?) {val target=state.selected;if(presentation!=null && matches(presentation) && !state.loading && target!=null)open(target,presentation.selection)}
    fun back(presentation:ClientWorkControl?):Boolean=if(presentation!=null && matches(presentation) && state.selected!=null)back(presentation.selection) else false
    fun clear() { back(); state = ClientWorkState() }
}
