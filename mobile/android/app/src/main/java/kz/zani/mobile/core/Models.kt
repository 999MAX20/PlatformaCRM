package kz.zani.mobile.core

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

data class Business(val id: Int, val name: String, val timezone: String)
data class Bootstrap(val activeBusiness: Business, val businesses: List<Business>)
data class Appointment(val id: Int, val title: String?, val status: String, val startAt: String?, val endAt: String?, val clientID: Int? = null) {
    val start: Instant get() = Instant.parse(startAt)
    val end: Instant get() = Instant.parse(endAt)
}
data class AppointmentList(val business: Int, val date: String, val items: List<Appointment>, val total: Int) {
    val isPartial: Boolean get() = total > items.size
}
data class Named(val id: Int?, val name: String?)
data class AppointmentDetail(val business: Int, val appointment: Appointment, val notes: String?, val service: Named?, val resource: Named?, val clientRefID: Int? = null, val relatedTasks: List<WorkTask>? = null, val maxRelated: Int? = null)
enum class ReadProblem { DENIED, NOT_FOUND, UNAVAILABLE, INVALID_PAYLOAD, INVALID_CONTEXT }
class ReadException(val problem: ReadProblem) : Exception(problem.name)
data class Selection(val business: Business, val day: String, val revision: Int)
data class DetailSelection(val scope: Selection, val id: Int, val revision: Int)

class AgendaSession {
    var businesses: List<Business> = emptyList(); private set
    var selection: Selection? = null; private set
    var items: List<Appointment> = emptyList(); private set
    var detail: AppointmentDetail? = null; private set
    var detailSelection: DetailSelection? = null; private set
    var isPartial = false; private set
    var responseDay: String? = null; private set
    val sourceDayMismatch: Boolean get() = responseDay != null && responseDay != selection?.day
    private var revision = 0
    fun install(bootstrap: Bootstrap) {
        val valid = runCatching {
            bootstrap.businesses.isNotEmpty() && bootstrap.businesses.map { it.id }.distinct().size == bootstrap.businesses.size &&
                bootstrap.businesses.any { it.id == bootstrap.activeBusiness.id && it.timezone == bootstrap.activeBusiness.timezone } &&
                bootstrap.businesses.all { it.id > 0 && ZoneId.of(it.timezone).id.isNotBlank() }
        }.getOrDefault(false)
        if (!valid) throw ReadException(ReadProblem.INVALID_PAYLOAD)
        revision++; businesses = bootstrap.businesses; selection = null; items = emptyList(); clearDetail(); isPartial = false; responseDay = null
    }
    fun begin(businessID: Int, day: String): Selection {
        val business = businesses.firstOrNull { it.id == businessID } ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
        if (runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not()) throw ReadException(ReadProblem.INVALID_CONTEXT)
        revision++; val scope = Selection(business, day, revision)
        selection = scope; items = emptyList(); clearDetail(); isPartial = false; responseDay = null
        return scope
    }
    fun receive(payload: AppointmentList, scope: Selection): Boolean {
        if (selection != scope) return false
        val valid = payload.business == scope.business.id && payload.total >= payload.items.size &&
            payload.items.map { it.id }.distinct().size == payload.items.size && payload.items.all { it.id > 0 }
        if (!valid) throw ReadException(ReadProblem.INVALID_PAYLOAD)
        items = payload.items; isPartial = payload.isPartial; responseDay = payload.date
        return true
    }
    fun beginDetail(id: Int): DetailSelection {
        val scope = selection ?: throw ReadException(ReadProblem.INVALID_CONTEXT)
        if (items.none { it.id == id }) throw ReadException(ReadProblem.INVALID_CONTEXT)
        revision++
        val request = DetailSelection(scope, id, revision)
        detail = null; detailSelection = request
        return request
    }
    fun receive(payload: AppointmentDetail, request: DetailSelection): Boolean {
        if (detailSelection != request || selection != request.scope) return false
        val scope = request.scope; val id = request.id
        val valid = payload.business == scope.business.id && payload.appointment.id == id && items.any { it.id == id }
        if (!valid) throw ReadException(ReadProblem.INVALID_PAYLOAD)
        items = items.map { if (it.id == id) payload.appointment else it }
        detail = payload; return true
    }
    fun clearDetail() { detail = null; detailSelection = null }
}
