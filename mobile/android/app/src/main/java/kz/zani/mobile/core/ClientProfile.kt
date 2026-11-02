package kz.zani.mobile.core

data class ClientVisit(val appointment: Appointment, val clientID: Int)
data class ClientProfile(val business: Int, val client: ClientContact, val notes: String?, val appointments: List<ClientVisit>, val maxRelated: Int, val tasks: List<WorkTask>? = null, val conversations: List<InboxConversation>? = null,val editReadFields: ClientEditReadFields?=null) {
    val historyCapped: Boolean get() = appointments.size == maxRelated
    fun validFor(scope: Int, id: Int) = runCatching {
        scope > 0 && id > 0 && business == scope && client.id == id && maxRelated > 0 && appointments.size <= maxRelated &&
            appointments.map { it.appointment.id }.distinct().size == appointments.size && appointments.all { it.clientID == id && it.appointment.id > 0 && it.appointment.end > it.appointment.start }
    }.getOrDefault(false)
}
