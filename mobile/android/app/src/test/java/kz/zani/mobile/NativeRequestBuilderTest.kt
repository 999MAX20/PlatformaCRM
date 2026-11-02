package kz.zani.mobile

import kz.zani.mobile.data.*
import org.junit.Assert.*
import org.junit.Test
import java.net.URI
import java.net.URLDecoder
import java.nio.charset.StandardCharsets

class NativeRequestBuilderTest {
    private fun failure(expected: RequestConfigurationProblem, block: () -> Unit) {
        try { block(); fail("Expected $expected") }
        catch (error: RequestConfigurationException) { assertEquals(expected, error.problem) }
    }
    @Test fun readOnlyDescriptorAndEncodedParameterValues() {
        val builder = NativeRequestBuilder(URI("https://fixture-api.example.invalid"), 7000)
        val request = builder.request(ReadRequest("/api/mobile/v1/appointments/", mapOf("business" to "101", "date" to "2026-10-28", "status" to "created&business=999 + К")))
        assertEquals("GET", request.method); assertEquals(7000L, request.timeoutMillis)
        assertEquals("application/json", request.headers["Accept"]); assertNull(request.headers["Authorization"])
        val values = request.uri.rawQuery.split("&").associate { val p = it.split("=", limit = 2); p[0] to URLDecoder.decode(p[1], StandardCharsets.UTF_8.name()) }
        assertEquals("created&business=999 + К", values["status"])
        assertEquals("101", values["business"])
    }
    @Test fun originCannotCarryCredentialsPathQueryOrFragment() {
        for (value in listOf("http://fixture-api.example.invalid", "https://user:pass@fixture-api.example.invalid", "https://fixture-api.example.invalid/api", "https://fixture-api.example.invalid?business=999", "https://fixture-api.example.invalid#fragment", "https://fixture-api.example.invalid:0")) {
            failure(RequestConfigurationProblem.INVALID_ORIGIN) { NativeRequestBuilder(URI(value), 7000) }
        }
    }
    @Test fun foreignTraversalAndEmbeddedQueryPathsAreRejected() {
        val builder = NativeRequestBuilder(URI("https://fixture-api.example.invalid"), 7000)
        for (path in listOf("//foreign.example.invalid/api/mobile/v1/appointments/", "/api/mobile/v1/../outside/", "/api/mobile/v1/%2e%2e/outside/", "/api/mobile/v1/appointments/?business=999", "/api/mobile/v1/appointments/#fragment", "/api/mobile/v1//appointments/")) {
            failure(RequestConfigurationProblem.INVALID_PATH) { builder.request(ReadRequest(path)) }
        }
    }
    @Test fun timeoutMustBeExplicitAndPositive() {
        failure(RequestConfigurationProblem.INVALID_TIMEOUT) { NativeRequestBuilder(URI("https://fixture-api.example.invalid"), 0) }
    }
}
