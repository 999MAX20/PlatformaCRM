package kz.zani.mobile.core

import java.time.LocalDate

// Source projection subsets; no client-side KPI joins or inferred permissions.
data class HomeAppointments(val today: Int)
data class HomeTasks(val open: Int)
data class HomeConversations(val open: Int, val unread: Int)
data class HomeSummary(val business: Int, val appointments: HomeAppointments?, val tasks: HomeTasks?, val conversations: HomeConversations?) {
    fun validFor(scope: Int) = scope > 0 && business == scope && (appointments?.today ?: 0) >= 0 && (tasks?.open ?: 0) >= 0 &&
        (conversations == null || conversations.open >= 0 && conversations.unread >= 0 && conversations.unread <= conversations.open)
}
data class TodayAppointments(val date: String, val total: Int, val items: List<Appointment>) { val partial: Boolean get() = total > items.size }
data class TodayTasks(val date: String, val total: Int, val overdue: Int, val items: List<WorkTask>) { val partial: Boolean get() = total > items.size }
data class TodaySummary(val business: Int, val date: String, val limit: Int, val maxItems: Int, val appointments: TodayAppointments?, val tasks: TodayTasks?) {
    fun validFor(scope: Int, day: String): Boolean {
        if (scope < 1 || business != scope || date != day || runCatching { LocalDate.parse(day).toString() == day }.getOrDefault(false).not() || limit !in 1..50 || maxItems != limit) return false
        if (appointments != null && (appointments.date != day || appointments.total < appointments.items.size || appointments.items.size > limit ||
                appointments.items.map { it.id }.distinct().size != appointments.items.size || appointments.items.any { it.id <= 0 || !runCatching { it.end > it.start }.getOrDefault(false) })) return false
        if (tasks != null && (tasks.date != day || tasks.total < tasks.items.size || tasks.overdue < 0 || tasks.items.size > limit ||
                tasks.items.map { it.id }.distinct().size != tasks.items.size || tasks.items.any { !it.valid() })) return false
        return true
    }
}
enum class HomeDestination(val key: String, val tabIndex: Int) { APPOINTMENTS("appointments", 1), CLIENTS("clients", 2), INBOX("inbox", 3), TASKS("tasks", 4) }
