package kz.zani.mobile.core

sealed interface AppointmentRelatedTarget { data class Client(val id: Int) : AppointmentRelatedTarget; data class Task(val id: Int) : AppointmentRelatedTarget; data class Service(val id:Int):AppointmentRelatedTarget;data class Resource(val id:Int):AppointmentRelatedTarget }
val AppointmentDetail.linkedClientID: Int? get() = appointment.clientID?.takeIf { it > 0 && it == clientRefID }
val AppointmentDetail.clientLinkAmbiguous: Boolean get() = linkedClientID == null && (appointment.clientID != null || clientRefID != null)
val AppointmentDetail.providedTasks: List<WorkTask>? get() {
    val tasks = relatedTasks ?: return null; val cap = maxRelated ?: return null
    return tasks.takeIf { cap in 1..5 && it.size <= cap && it.all { task -> task.valid() } && it.map { task -> task.id }.distinct().size == it.size }
}
val AppointmentDetail.relatedTaskWindowCapped: Boolean get() = providedTasks?.let { it.size == maxRelated } ?: false

val AppointmentRelatedTarget.referenceKind:AppointmentReferenceKind? get()=when(this){is AppointmentRelatedTarget.Service->AppointmentReferenceKind.SERVICE;is AppointmentRelatedTarget.Resource->AppointmentReferenceKind.RESOURCE;else->null}
