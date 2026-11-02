package kz.zani.mobile

import kz.zani.mobile.core.ReadException
import kz.zani.mobile.core.ReadProblem
import kz.zani.mobile.data.JsonContracts
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class JsonContractsTest {
    private fun fixture(name: String) = JSONObject(javaClass.classLoader!!.getResourceAsStream("fixtures/$name.json")!!.bufferedReader().use { it.readText() })
    private fun rejected(json: JSONObject, parse: (String) -> Any) {
        try { parse(json.toString()); fail("Wrong JSON type was accepted: $json") }
        catch (error: ReadException) { assertEquals(ReadProblem.INVALID_PAYLOAD, error.problem) }
    }
    @Test fun idsAndTotalsDoNotCoerceStringsFractionsOrOverflow() {
        for (bad in listOf<Any>("501", 501.5, true, 4294967797L)) {
            val detail = fixture("appointment-101-501"); detail.getJSONObject("appointment").put("id", bad)
            rejected(detail, JsonContracts::detail)
        }
        val list = fixture("appointments-101"); list.getJSONObject("summary").put("total", "3")
        rejected(list, JsonContracts::appointments)
    }
    @Test fun textFieldsDoNotStringifyNumbersOrBooleans() {
        for (key in listOf("title", "status", "start_at", "end_at")) {
            val detail = fixture("appointment-101-501"); detail.getJSONObject("appointment").put(key, 123)
            rejected(detail, JsonContracts::detail)
        }
        val detail = fixture("appointment-101-501"); detail.getJSONObject("details").put("notes", false)
        rejected(detail, JsonContracts::detail)
    }
    @Test fun optionalObjectsMustBeObjectsOrNull() {
        for (key in listOf("service", "resource")) {
            for (bad in listOf<Any>("withheld", 1, false)) {
                val detail = fixture("appointment-101-501"); detail.getJSONObject("details").put(key, bad)
                rejected(detail, JsonContracts::detail)
            }
        }
    }
    @Test fun namedFieldsAndBootstrapUseTheSameStrictTypes() {
        val detail = fixture("appointment-101-501"); detail.getJSONObject("details").getJSONObject("resource").put("id", "11")
        rejected(detail, JsonContracts::detail)
        val bootstrap = fixture("bootstrap"); bootstrap.getJSONObject("active_business").put("name", 101)
        rejected(bootstrap, JsonContracts::bootstrap)
    }
    @Test fun explicitNullAndUnknownFieldsRemainCompatible() {
        val detail = fixture("appointment-101-501"); val fields = detail.getJSONObject("details")
        detail.getJSONObject("appointment").put("title", JSONObject.NULL); fields.put("notes", JSONObject.NULL)
        fields.put("service", JSONObject.NULL); fields.getJSONObject("resource").put("id", JSONObject.NULL).put("name", JSONObject.NULL)
        detail.put("future_field", JSONObject().put("ignored", true))
        detail.getJSONObject("appointment").put("id", 501.0)
        val decoded = JsonContracts.detail(detail.toString())
        assertEquals(501, decoded.appointment.id); assertNull(decoded.appointment.title); assertNull(decoded.notes); assertNull(decoded.service)
        assertNull(decoded.resource!!.id); assertNull(decoded.resource!!.name)
    }
}
