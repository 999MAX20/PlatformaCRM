package kz.zani.mobile.data
import kz.zani.mobile.core.*

fun interface TeamMemberReadRepository {suspend fun member(business:Int,id:Int):TeamMemberReadSource}
class APITeamMemberReadRepository(private val transport:ReadTransport):TeamMemberReadRepository {
    override suspend fun member(business:Int,id:Int):TeamMemberReadSource {if(business<=0 || id<=0)throw ReadException(ReadProblem.INVALID_CONTEXT);val r=transport.get(ReadRequest("/api/team/members/$id/"));if(r.status!=200)throw ReadException(when(r.status){403->ReadProblem.DENIED;404->ReadProblem.NOT_FOUND;else->ReadProblem.UNAVAILABLE});return TeamMemberReadSource.decode(r.body,business,id) ?: throw ReadException(ReadProblem.INVALID_PAYLOAD)}
}
