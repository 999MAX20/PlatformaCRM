package kz.zani.mobile.data
import kz.zani.mobile.core.*

fun interface DealReadRepository {suspend fun deal(business:Int,id:Int):DealReadSource}
class APIDealReadRepository(private val transport:ReadTransport):DealReadRepository {
    override suspend fun deal(business:Int,id:Int):DealReadSource {if(business<=0 || id<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/deals/$id/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return DealReadSource.decode(r.body,business,id) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
