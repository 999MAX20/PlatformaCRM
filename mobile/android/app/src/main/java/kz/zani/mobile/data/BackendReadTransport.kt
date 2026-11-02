package kz.zani.mobile.data

import java.net.URI
import java.nio.charset.CharacterCodingException
import javax.net.ssl.HttpsURLConnection
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.runInterruptible
import kotlinx.coroutines.Dispatchers
import kz.zani.mobile.core.*

// Caller-owned configured HTTP/session seam, separate from data repositories and commands.
fun interface NativeReadHTTPExchange {suspend fun execute(request:NativeReadDescriptor):ReadResponse}
class BackendReadTransport(private val builder:NativeRequestBuilder,private val exchange:NativeReadHTTPExchange):ReadTransport {
    override suspend fun get(request:ReadRequest):ReadResponse {
        currentCoroutineContext().ensureActive()
        val descriptor=builder.request(request)
        val response=exchange.execute(descriptor)
        currentCoroutineContext().ensureActive()
        return response
    }
}
// No default connection/session, credentials, retry or fixture fallback.
// Caller supplies an approved configured HTTPS connection; local tests never create one.
class URLConnectionReadExchange(private val connectionFactory:(URI)->HttpsURLConnection):NativeReadHTTPExchange {
    override suspend fun execute(request:NativeReadDescriptor):ReadResponse {
        if(request.method!="GET")throw RequestConfigurationException(RequestConfigurationProblem.INVALID_PATH)
        if(request.timeoutMillis !in 1..Int.MAX_VALUE.toLong())throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)
        return runInterruptible(Dispatchers.IO) {
            val connection=connectionFactory(request.uri)
            try {
                connection.requestMethod="GET";connection.doOutput=false
                connection.connectTimeout=request.timeoutMillis.toInt();connection.readTimeout=request.timeoutMillis.toInt()
                request.headers.forEach {(key,value)->connection.setRequestProperty(key,value)}
                val status=connection.responseCode
                val stream=if(status>=400)connection.errorStream else connection.inputStream
                val bytes=stream?.use {it.readBytes()} ?: ByteArray(0)
                // Successful DTO text must be valid UTF8; error classification keeps raw HTTP status.
                val body=try {bytes.decodeToString(throwOnInvalidSequence=status==200)} catch(error:CharacterCodingException) {throw ReadException(ReadProblem.INVALID_PAYLOAD)}
                ReadResponse(status,body)
            } finally {connection.disconnect()}
        }
    }
}
