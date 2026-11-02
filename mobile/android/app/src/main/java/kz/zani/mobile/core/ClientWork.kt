package kz.zani.mobile.core

// Local read selection, not a server DTO or an access grant.
data class ClientReadSelection(val business: Int, val id: Int, val revision: Int)
sealed interface ClientWorkTarget {
    data class Task(val id: Int) : ClientWorkTarget
    data class Conversation(val id: Int) : ClientWorkTarget
    data class Appointment(val id: Int) : ClientWorkTarget
}
val ClientProfile.providedAppointments: List<Appointment>? get() = appointments.takeIf { rows ->
    maxRelated in 1..5 && rows.size <= maxRelated && rows.map { it.appointment.id }.distinct().size == rows.size && rows.all { it.clientID == client.id && it.appointment.id > 0 }
}?.map { it.appointment }
val ClientProfile.providedTasks: List<WorkTask>? get() = tasks?.takeIf { rows ->
    maxRelated in 1..5 && rows.size <= maxRelated && rows.map { it.id }.distinct().size == rows.size && rows.all { it.valid() && it.clientID == client.id }
}
val ClientProfile.providedConversations: List<InboxConversation>? get() = conversations?.takeIf { rows ->
    maxRelated in 1..5 && rows.size <= maxRelated && rows.map { it.id }.distinct().size == rows.size && rows.all { it.id > 0 && it.unreadCount >= 0 }
}
