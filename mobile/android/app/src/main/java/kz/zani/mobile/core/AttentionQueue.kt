package kz.zani.mobile.core

data class AttentionIdentity(val key: String, val type: String, val entityID: Int)
enum class AttentionKind { TASK, CONVERSATION, APPOINTMENT }
data class AttentionTarget(val kind: AttentionKind, val id: Int)
data class AttentionEntity(val id: Int, val title: String?, val href: String?)
data class AttentionItem(val key: String, val type: String, val priority: Int, val entity: AttentionEntity) {
    val identity: AttentionIdentity get() = AttentionIdentity(key, type, entity.id)
    val stableKey: String get() = "${key.length}:$key${type.length}:$type:${entity.id}"
    // ID and type are explicit fields; href only confirms an exact source template.
    val readTarget: AttentionTarget? get() = if (entity.id <= 0) null else when {
        key == "complete_task" && type == "task" && entity.href == "/app/tasks?task=${entity.id}" -> AttentionTarget(AttentionKind.TASK, entity.id)
        key == "reply_conversation" && type == "conversation" && entity.href == "/app/conversations?conversation=${entity.id}" -> AttentionTarget(AttentionKind.CONVERSATION, entity.id)
        key == "confirm_appointment" && type == "appointment" && entity.href == "/app/calendar?appointment=${entity.id}" -> AttentionTarget(AttentionKind.APPOINTMENT, entity.id)
        else -> null
    }
}
data class AttentionPage(val business: Int, val limit: Int, val total: Int, val items: List<AttentionItem>, val maxItems: Int) {
    val windowCapped: Boolean get() = items.size == limit
    fun validFor(scope: Int) = scope > 0 && business == scope && limit in 1..50 && maxItems == limit && total == items.size && items.size <= limit &&
        items.all { it.entity.id > 0 } && items.map { it.identity }.distinct().size == items.size
}
sealed interface AttentionDetail {
    data class TaskRead(val value: TaskDetails) : AttentionDetail
    data class ThreadRead(val value: InboxThread) : AttentionDetail
    data class AppointmentRead(val value: AppointmentDetail) : AttentionDetail
    val title: String? get() = when (this) { is TaskRead -> value.task.title; is ThreadRead -> value.conversation.title; is AppointmentRead -> value.appointment.title }
    fun validFor(business: Int, target: AttentionTarget): Boolean = when (this) {
        is TaskRead -> target.kind == AttentionKind.TASK && value.validFor(business, target.id)
        is ThreadRead -> target.kind == AttentionKind.CONVERSATION && value.validFor(business, target.id)
        is AppointmentRead -> target.kind == AttentionKind.APPOINTMENT && runCatching { value.business == business && value.appointment.id == target.id && value.appointment.end > value.appointment.start }.getOrDefault(false)
    }
}
