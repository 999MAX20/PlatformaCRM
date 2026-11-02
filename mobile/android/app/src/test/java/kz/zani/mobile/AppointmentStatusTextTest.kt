package kz.zani.mobile

import kz.zani.mobile.core.AppointmentStatusText
import kz.zani.mobile.data.UiCopy
import kz.zani.mobile.data.JsonContracts
import org.junit.Assert.*
import org.junit.Test

class AppointmentStatusTextTest {
    private fun resource(path: String) = javaClass.classLoader!!.getResourceAsStream(path)!!.bufferedReader().use { it.readText() }
    @Test fun allSixSourceStatusesUseExistingLocaleLabels() {
        val statuses = listOf("created" to "appointmentCreated","confirmed" to "appointmentConfirmed","cancelled" to "appointmentCancelled","rescheduled" to "appointmentRescheduled","completed" to "appointmentCompleted","no_show" to "appointmentNoShow")
        for (language in listOf("ru","kk","en")) {
            val copy = UiCopy(resource("ui-copy.json"),language)
            for ((raw,key) in statuses) assertEquals(copy.text(key),AppointmentStatusText.label(raw,copy::text))
        }
    }
    @Test fun emptyStatusIsUnavailableAndFutureSourceValueIsNotGuessed() {
        for (language in listOf("ru","kk","en")) {
            val copy = UiCopy(resource("ui-copy.json"),language)
            for (raw in listOf(null,"","  \n")) assertEquals(copy.text("notAvailable"),AppointmentStatusText.label(raw,copy::text))
            assertEquals("future_source_status",AppointmentStatusText.label("future_source_status",copy::text))
        }
    }
    @Test fun displayDoesNotConvertStoredStateOrIdentity() {
        val detail = JsonContracts.detail(resource("fixtures/appointment-101-501.json"))
        val copy = UiCopy(resource("ui-copy.json"),"kk")
        assertEquals(copy.text("appointmentConfirmed"),AppointmentStatusText.label(detail.appointment.status,copy::text))
        assertEquals("confirmed",detail.appointment.status); assertEquals(501,detail.appointment.id)
    }
}
