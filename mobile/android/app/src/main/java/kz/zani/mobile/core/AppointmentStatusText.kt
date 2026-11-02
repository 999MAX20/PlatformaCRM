package kz.zani.mobile.core

// Presentation only: API values and lifecycle rules remain unchanged.
object AppointmentStatusText {
    fun label(raw: String?,text: (String) -> String): String = when (raw) {
        "created" -> text("appointmentCreated")
        "confirmed" -> text("appointmentConfirmed")
        "cancelled" -> text("appointmentCancelled")
        "rescheduled" -> text("appointmentRescheduled")
        "completed" -> text("appointmentCompleted")
        "no_show" -> text("appointmentNoShow")
        else -> raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    }
}
