package kz.zani.mobile.core

// Syntax only: no ingress grant, transport, session, origin or navigation.
// Long keeps the untrusted route ID separate from the independent source Int.
class RelativeAppointmentCandidate private constructor(val raw:String,val appointmentID:Long) {
    fun corroboratedTarget(source:CRMNotification):Int? = source.appointmentTarget
        ?.takeIf { source.valid() && it.toLong()==appointmentID }
    companion object {
        fun parse(raw:String):RelativeAppointmentCandidate? {
            val query="/app/calendar?appointment=";val path="/app/calendar/"
            val digits=when {
                raw.startsWith(query)->raw.substring(query.length)
                raw.startsWith(path)->raw.substring(path.length).removeSuffix("/")
                else->return null
            }
            if(digits.isEmpty() || digits.any { it !in '0'..'9' })return null
            val id=digits.toLongOrNull()?.takeIf { it>0 && it.toString()==digits } ?: return null
            return RelativeAppointmentCandidate(raw,id)
        }
    }
}
