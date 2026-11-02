package kz.zani.mobile.core

import java.time.Instant

data class CRMNotification(val id: Int, val text: String?, val category: String?, val priority: String?, val status: String?, val channel: String?,
    val sendAt: String?, val readAt: String?, val readMarkerPresent: Boolean, val actionURL: String?, val appointmentID: Int?) {
    val unread: Boolean get() = readMarkerPresent && readAt == null
    val appointmentTarget: Int? get() {
        val id = appointmentID?.takeIf { it > 0 } ?: return null
        return id.takeIf { actionURL in listOf("/app/calendar?appointment=$id", "/app/calendar/$id", "/app/calendar/$id/") }
    }
    fun valid() = id > 0 && listOfNotNull(sendAt, readAt).all { runCatching { Instant.parse(it) }.isSuccess }
}
data class NotificationPage(val business: Int, val items: List<CRMNotification>, val total: Int) {
    fun validFor(scope: Int) = scope > 0 && business == scope && total >= items.size && items.all { it.valid() } && items.map { it.id }.distinct().size == items.size
}
