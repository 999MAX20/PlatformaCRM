package kz.zani.mobile.data

import java.net.URI

// Explicit public inputs; no env/file/credential access or production defaults.
enum class NativeConnectionConfigurationProblem {UNCONFIGURED,UNEXPECTED_KEY}
class NativeConnectionConfigurationException(val problem:NativeConnectionConfigurationProblem):Exception(problem.name)
class NativeConnectionConfiguration(publicValues:Map<String,String>) {
    val origin:URI
    val timeoutMillis:Long
    init {
        if(!setOf("CRM_API_ORIGIN","CRM_READ_TIMEOUT_SECONDS").containsAll(publicValues.keys))throw NativeConnectionConfigurationException(NativeConnectionConfigurationProblem.UNEXPECTED_KEY)
        val rawOrigin=publicValues["CRM_API_ORIGIN"]?.trim().orEmpty();val rawTimeout=publicValues["CRM_READ_TIMEOUT_SECONDS"]?.trim().orEmpty()
        if(rawOrigin.isEmpty() || rawTimeout.isEmpty())throw NativeConnectionConfigurationException(NativeConnectionConfigurationProblem.UNCONFIGURED)
        origin=try {URI(rawOrigin)} catch(error:Exception) {throw RequestConfigurationException(RequestConfigurationProblem.INVALID_ORIGIN)}
        if(!Regex("^[0-9]+(?:\\.[0-9]{1,3})?$").matches(rawTimeout))throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)
        val parts=rawTimeout.split('.');val seconds=parts[0].toLongOrNull() ?: throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)
        val millis=parts.getOrElse(1) {""}.padEnd(3,'0').toLong()
        timeoutMillis=try {Math.addExact(Math.multiplyExact(seconds,1000),millis)} catch(error:ArithmeticException) {throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)}
        if(timeoutMillis<=0)throw RequestConfigurationException(RequestConfigurationProblem.INVALID_TIMEOUT)
        NativeRequestBuilder(origin,timeoutMillis)
    }
    fun requestBuilder()=NativeRequestBuilder(origin,timeoutMillis)
}
