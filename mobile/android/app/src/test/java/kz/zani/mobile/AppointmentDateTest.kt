package kz.zani.mobile

import kz.zani.mobile.ui.formatAppointmentDate
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class AppointmentDateTest {
    private fun fixtureStart(): String {
        val json = javaClass.classLoader!!.getResourceAsStream("fixtures/appointment-101-501.json")!!.bufferedReader().use { it.readText() }
        return JSONObject(json).getJSONObject("appointment").getString("start_at")
    }
    @Test fun fixtureShowsBusinessTimeInEverySupportedLanguage() {
        for (language in listOf("ru", "kk", "en")) {
            val label = formatAppointmentDate(fixtureStart(), "Asia/Almaty", language)
            assertTrue("$language detail must show Business-local09:00, got $label", label?.contains("9:00") == true)
            assertFalse(label!!.contains("T04:00"))
        }
    }
    @Test fun businessZoneCanRollDateIntoNextDay() {
        for (language in listOf("ru", "kk", "en")) {
            val label = formatAppointmentDate("2026-10-28T23:30:00Z", "Asia/Almaty", language)!!
            assertTrue("Local day must be29, got $label", label.contains("29"))
            assertTrue("Local time must be04:30, got $label", label.contains("4:30"))
        }
    }
    @Test fun sameInstantUsesSelectedBusinessZone() {
        val utc = formatAppointmentDate(fixtureStart(), "UTC", "en")!!
        val almaty = formatAppointmentDate(fixtureStart(), "Asia/Almaty", "en")!!
        assertTrue(utc.contains("4:00")); assertTrue(almaty.contains("9:00")); assertNotEquals(utc, almaty)
    }
    @Test fun missingOrInvalidContextDoesNotGuessUtc() {
        assertNull(formatAppointmentDate(fixtureStart(), null, "ru"))
        assertNull(formatAppointmentDate(fixtureStart(), "Invalid/Zone", "kk"))
        assertNull(formatAppointmentDate("not-an-instant", "Asia/Almaty", "en"))
    }
}
