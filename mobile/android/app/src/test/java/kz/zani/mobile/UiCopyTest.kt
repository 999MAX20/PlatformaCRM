package kz.zani.mobile

import kz.zani.mobile.data.UiCopy
import kz.zani.mobile.core.ReadException
import kz.zani.mobile.core.ReadProblem
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class UiCopyTest {
    private fun source() = javaClass.classLoader!!.getResourceAsStream("ui-copy.json")!!.bufferedReader().use { it.readText() }
    @Test fun regionTagsAndUnsupportedLocaleFallback() {
        for ((tag, expected) in listOf("ru-KZ" to "ru", "KK_kz" to "kk", "en-US" to "en", "de-DE" to "en", "" to "en")) {
            val copy = UiCopy(source(), tag)
            assertEquals(expected, copy.language)
            assertTrue(copy.text("appointments").isNotBlank())
        }
    }
    @Test fun genericCRMTerminology() {
        assertEquals("Специалист", UiCopy(source(), "ru").text("resource"))
        assertEquals("Маман", UiCopy(source(), "kk").text("resource"))
    }
    @Test fun missingTranslationIsNotSilentlyAccepted() {
        val broken = JSONObject(source())
        broken.getJSONObject("kk").remove("resource")
        try { UiCopy(broken.toString(), "kk"); fail("Missing key accepted") }
        catch (error: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, error.problem) }
    }
    @Test fun allSupportedLocalesUseSameKeySet() {
        val en = UiCopy(source(), "en").values.keys
        assertEquals(en, UiCopy(source(), "ru").values.keys)
        assertEquals(en, UiCopy(source(), "kk").values.keys)
    }
}
