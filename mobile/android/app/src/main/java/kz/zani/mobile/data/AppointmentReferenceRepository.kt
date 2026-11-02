package kz.zani.mobile.data

import kz.zani.mobile.core.*

interface AppointmentReferenceRepository {suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int):AppointmentReferenceDetail}
class APIAppointmentReferenceRepository(private val transport:ReadTransport):AppointmentReferenceRepository {
    override suspend fun reference(kind:AppointmentReferenceKind,business:Int,id:Int):AppointmentReferenceDetail {
        val path=kind.path(id);if(business<=0 || path==null)throw ReadException(ReadProblem.INVALID_CONTEXT)
        val response=transport.get(ReadRequest(path))
        return when(response.status) {
            200->AppointmentReferenceDetail.decode(response.body,kind)?.takeIf {it.validFor(business,id)} ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)
            403->throw ReadException(ReadProblem.DENIED);404->throw ReadException(ReadProblem.NOT_FOUND);else->throw ReadException(ReadProblem.UNAVAILABLE)
        }
    }
}
