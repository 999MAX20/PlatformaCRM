package kz.zani.mobile.data

import kz.zani.mobile.core.*
import java.time.LocalDate

data class ReadRequest(val path: String, val query: Map<String, String> = emptyMap())
data class ReadResponse(val status: Int, val body: String)
fun interface ReadTransport { suspend fun get(request: ReadRequest): ReadResponse }
interface AgendaRepository {
    suspend fun bootstrap(): Bootstrap
    suspend fun appointments(business: Int, day: String): AppointmentList
    suspend fun appointment(business: Int, id: Int): AppointmentDetail
}
fun interface ClientRepository { suspend fun clients(business: Int): ClientList }
interface ClientSearchRepository : ClientProfileRepository { suspend fun searchClients(business: Int,search: String): ClientList }
interface InboxRepository {
    suspend fun inbox(business: Int): InboxList
    suspend fun thread(business: Int, id: Int): InboxThread
}
interface TaskReadRepository {
    suspend fun tasks(business: Int): TaskPage
    suspend fun taskDetails(business: Int, id: Int): TaskDetails
}
interface TaskQueryRepository: TaskReadRepository {suspend fun tasks(business: Int,filter: TaskQueryFilter): TaskPage}
interface NotificationRepository {
    suspend fun notifications(business: Int): NotificationPage
    suspend fun appointment(business: Int, id: Int): AppointmentDetail
}
fun interface ClientProfileRepository { suspend fun clientProfile(business: Int, id: Int): ClientProfile }
interface InboxClientRepository : InboxRepository, ClientProfileRepository
interface ClientWorkRepository {
    suspend fun taskDetails(business: Int, id: Int): TaskDetails
    suspend fun thread(business: Int, id: Int): InboxThread
    suspend fun appointment(business: Int, id: Int): AppointmentDetail
}
interface HomeTodayRepository {
    suspend fun home(business: Int): HomeSummary
    suspend fun today(business: Int, day: String): TodaySummary
}
interface AttentionRepository {
    suspend fun actions(business: Int): AttentionPage
    suspend fun taskDetails(business: Int, id: Int): TaskDetails
    suspend fun thread(business: Int, id: Int): InboxThread
    suspend fun appointment(business: Int, id: Int): AppointmentDetail
}
interface AppointmentRelatedRepository : ClientProfileRepository { suspend fun taskDetails(business: Int, id: Int): TaskDetails }
class APIReadRepository(private val transport: ReadTransport) : AgendaRepository, ClientRepository, ClientSearchRepository, InboxRepository, InboxClientRepository, TaskQueryRepository, NotificationRepository, ClientProfileRepository, ClientWorkRepository, HomeTodayRepository, AttentionRepository, AppointmentRelatedRepository {
    private suspend fun body(request: ReadRequest): String {
        val response = transport.get(request)
        return when (response.status) {
            200 -> response.body
            403 -> throw ReadException(ReadProblem.DENIED)
            404 -> throw ReadException(ReadProblem.NOT_FOUND)
            else -> throw ReadException(ReadProblem.UNAVAILABLE)
        }
    }
    override suspend fun actions(business: Int): AttentionPage {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.actions(body(ReadRequest("/api/mobile/v1/actions/", mapOf("business" to "$business", "limit" to "20"))))
    }
    override suspend fun home(business: Int): HomeSummary {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.home(body(ReadRequest("/api/mobile/v1/home/", mapOf("business" to "$business", "limit" to "5"))))
    }
    override suspend fun today(business: Int, day: String): TodaySummary {
        if (business < 1 || runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.today(body(ReadRequest("/api/mobile/v1/today/", mapOf("business" to "$business", "date" to day, "limit" to "20"))))
    }
    override suspend fun bootstrap() = JsonContracts.bootstrap(body(ReadRequest("/api/mobile/v1/bootstrap/")))
    override suspend fun clientProfile(business: Int, id: Int): ClientProfile {
        if (business < 1 || id < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.clientProfile(body(ReadRequest("/api/mobile/v1/clients/$id/", mapOf("business" to "$business"))))
    }
    override suspend fun notifications(business: Int): NotificationPage {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.notifications(body(ReadRequest("/api/mobile/v1/notifications/", mapOf("business" to "$business", "limit" to "50"))))
    }
    override suspend fun tasks(business: Int): TaskPage {
        return tasks(business,TaskQueryFilter())
    }
    override suspend fun tasks(business: Int,filter: TaskQueryFilter): TaskPage {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.tasks(body(ReadRequest("/api/mobile/v1/tasks/",filter.query(business))))
    }
    override suspend fun taskDetails(business: Int, id: Int): TaskDetails {
        if (business < 1 || id < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.taskDetails(body(ReadRequest("/api/mobile/v1/tasks/$id/", mapOf("business" to "$business"))))
    }
    override suspend fun inbox(business: Int): InboxList {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.inbox(body(ReadRequest("/api/mobile/v1/inbox/", mapOf("business" to "$business", "limit" to "50"))))
    }
    override suspend fun thread(business: Int, id: Int): InboxThread {
        if (business < 1 || id < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.thread(body(ReadRequest("/api/mobile/v1/inbox/$id/", mapOf("business" to "$business", "limit" to "30"))))
    }
    override suspend fun searchClients(business: Int,search: String): ClientList {
        if(business<1)throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.clients(body(ReadRequest("/api/mobile/v1/clients/",mapOf("business" to "$business","limit" to "50","search" to SourceTextTrim.pythonStrip(search)))))
    }
    override suspend fun clients(business: Int): ClientList {
        if (business < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.clients(body(ReadRequest("/api/mobile/v1/clients/", mapOf("business" to "$business", "limit" to "50"))))
    }
    override suspend fun appointments(business: Int, day: String): AppointmentList {
        if (business < 1 || runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.appointments(body(ReadRequest("/api/mobile/v1/appointments/", mapOf("business" to "$business", "date" to day, "limit" to "50"))))
    }
    override suspend fun appointment(business: Int, id: Int): AppointmentDetail {
        if (business < 1 || id < 1) throw ReadException(ReadProblem.INVALID_CONTEXT)
        return JsonContracts.detail(body(ReadRequest("/api/mobile/v1/appointments/$id/", mapOf("business" to "$business"))))
    }
}
