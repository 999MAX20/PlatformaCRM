package kz.zani.mobile.core

import java.time.Instant

// Read consumers of _task_item/build_mobile_task_detail; no lifecycle commands.
// Existing data-class equality keeps exact free text, including nil/empty; metadata rules remain unchanged.
data class WorkTask(val id: Int, val title: String?, val status: String, val priority: String?, val dueAt: String?, val clientID: Int? = null, val business: Int?=null, val cancelledAt: String?=null, val cancelledBy: Int?=null, val cancelReason: String?=null, val updatedAt: String?=null, val description: String?=null, val createdBy: Int?=null, val createdAt: String?=null) {
    fun valid() = id > 0 && (dueAt == null || runCatching { Instant.parse(dueAt) }.isSuccess)
}
data class TaskPage(val business: Int, val items: List<WorkTask>, val total: Int) {
    fun validFor(scope: Int) = scope > 0 && business == scope && total >= items.size && items.all { it.valid() } && items.map { it.id }.distinct().size == items.size
}
data class TaskComment(val id: Int, val text: String?, val createdAt: String?, val task: Int?=null, val author: Int?=null, val authorName: String?=null, val authorEmail: String?=null, val authorRead: MobileUserRead=MobileUserRead.Unknown)
// Explicit nullable source read only, no effective Task status or notification claim.
sealed interface TaskScheduleValue {
    data object NotSet: TaskScheduleValue
    data object Unknown: TaskScheduleValue
    data class At(val raw: String): TaskScheduleValue
}
data class TaskDetails(val business: Int, val task: WorkTask, val description: String?, val comments: List<TaskComment>, val maxComments: Int, val appointmentID: Int? = null, val reminderAt: TaskScheduleValue=TaskScheduleValue.Unknown, val snoozedUntil: TaskScheduleValue=TaskScheduleValue.Unknown, val createdBy: MobileUserRead=MobileUserRead.Unknown, val assignee: MobileUserRead=MobileUserRead.Unknown,val appointmentRead:TaskAppointmentOriginal=TaskAppointmentOriginal.Unknown,val clientRead:TaskClientOriginal=TaskClientOriginal.Unknown) {
    val commentsCapped: Boolean get() = comments.size == maxComments
    fun validFor(scope: Int, id: Int) = scope > 0 && id > 0 && business == scope && task.id == id && task.valid() &&
        maxComments > 0 && comments.size <= maxComments && comments.all { it.id > 0 } && comments.map { it.id }.distinct().size == comments.size
}
