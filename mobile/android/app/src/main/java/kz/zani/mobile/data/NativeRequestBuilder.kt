package kz.zani.mobile.data

import java.net.URI
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.Locale

enum class RequestConfigurationProblem { INVALID_ORIGIN, INVALID_PATH, INVALID_TIMEOUT }
class RequestConfigurationException(val problem: RequestConfigurationProblem) : Exception(problem.name)
data class NativeReadDescriptor(val uri: URI, val timeoutMillis: Long, val method: String = "GET", val headers: Map<String, String> = mapOf("Accept" to "application/json"))

/** Pure request construction only; no connection, SDK setting or credential access. */
class NativeRequestBuilder(private val origin: URI, private val timeoutMillis: Long) {
    init {
        if (origin.scheme?.lowercase(Locale.ROOT) != "https" || origin.host == null || origin.rawUserInfo != null ||
            origin.rawQuery != null || origin.rawFragment != null || origin.path !in listOf("", "/") ||
            (origin.port != -1 && origin.port !in 1..65535)) throw RequestConfigurationException(RequestConfigurationProblem.INVALID_ORIGIN)
        if (timeoutMillis <= 0) throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)
    }
    fun request(read: ReadRequest): NativeReadDescriptor {
        if (read.path.contains("//") || !Regex("^/api/mobile/v1/[A-Za-z0-9/_-]+/$").matches(read.path)) throw RequestConfigurationException(RequestConfigurationProblem.INVALID_PATH)
        val base = URI(origin.scheme, origin.rawAuthority, read.path, null, null).toASCIIString()
        fun encoded(value: String) = URLEncoder.encode(value, StandardCharsets.UTF_8.name())
        val query = read.query.toSortedMap().entries.joinToString("&") { encoded(it.key) + "=" + encoded(it.value) }
        return NativeReadDescriptor(URI(base + if (query.isEmpty()) "" else "?$query"), timeoutMillis)
    }
}
