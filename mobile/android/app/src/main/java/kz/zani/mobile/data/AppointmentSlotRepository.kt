package kz.zani.mobile.data

import kz.zani.mobile.core.*

interface AppointmentSlotRepository {suspend fun slots(intent:AppointmentSlotIntent):AppointmentSlotRead}
class APIAppointmentSlotRepository(private val transport:ReadTransport):AppointmentSlotRepository {
    override suspend fun slots(intent:AppointmentSlotIntent):AppointmentSlotRead {
        if(!intent.valid)throw ReadException(ReadProblem.INVALID_CONTEXT)
        val response=transport.get(ReadRequest("/api/appointments/available-slots/",intent.query))
        return when(response.status) {
            200->AppointmentSlotRead.decode(response.body,intent) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)
            403->throw ReadException(ReadProblem.DENIED);404->throw ReadException(ReadProblem.NOT_FOUND);else->throw ReadException(ReadProblem.UNAVAILABLE)
        }
    }
}
