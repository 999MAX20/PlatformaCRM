package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun AttentionTargetContent(detail: AttentionDetail, timezone: String?, language: String, copy: Map<String, String>, modifier: Modifier) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun date(raw: String?) = raw?.let { formatAppointmentDate(it, timezone, language) } ?: text("notAvailable")
    fun status(raw: String) = when (raw) { "open" -> text("taskOpen"); "in_progress" -> text("taskInProgress"); "done" -> text("taskDone"); "cancelled" -> text("taskCancelled"); else -> raw }
    fun priority(raw: String?) = when (raw) { "low" -> text("priorityLow"); "normal" -> text("priorityNormal"); "high" -> text("priorityHigh"); "urgent" -> text("priorityUrgent"); else -> value(raw) }
    fun sender(raw: String?) = when (raw) { "client" -> text("senderClient"); "manager" -> text("senderManager"); "ai" -> text("senderAi"); else -> value(raw) }
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    LazyColumn(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text(text("readOnly"), style = MaterialTheme.typography.labelSmall) }
        when (detail) {
            is AttentionDetail.TaskRead -> {
                val d = detail.value
                item {
                    Text(value(d.task.title), style = MaterialTheme.typography.titleMedium)
                    Text("${text("status")}: ${status(d.task.status)}"); Text("${text("taskPriority")}: ${priority(d.task.priority)}")
                    Text("${text("taskDue")}: ${date(d.task.dueAt)}"); Text("${text("taskDescription")}: ${value(d.description)}")
                    Text(text("taskComments"), style = MaterialTheme.typography.titleMedium)
                    if (d.commentsCapped) Text(text("partial"), modifier = announcement)
                    if (d.comments.isEmpty()) Text(text("taskNoComments"))
                }
                items(d.comments, key = { it.id }) { comment -> Column(Modifier.semantics(mergeDescendants = true) {}) { Text(value(comment.text)); Text(date(comment.createdAt), style = MaterialTheme.typography.labelSmall) } }
            }
            is AttentionDetail.ThreadRead -> {
                val d = detail.value
                item {
                    Text(value(d.conversation.title), style = MaterialTheme.typography.titleMedium)
                    Text("${text("channel")}: ${ReadChannelText.label(d.conversation.channel,::text)}"); Text("${text("unread")}: ${d.conversation.unreadCount}")
                    if (d.windowCapped) Text(text("partial"), modifier = announcement)
                    if (d.messages.isEmpty()) Text(text("messagesEmpty"))
                }
                items(d.messages, key = { it.id }) { message -> Column(Modifier.semantics(mergeDescendants = true) {}) { Text(sender(message.senderType), style = MaterialTheme.typography.labelSmall); Text(value(message.text)); Text(date(message.createdAt), style = MaterialTheme.typography.labelSmall) } }
            }
            is AttentionDetail.AppointmentRead -> {
                val d = detail.value
                item {
                    Text(value(d.appointment.title), style = MaterialTheme.typography.titleMedium); Text("${text("status")}: ${AppointmentStatusText.label(d.appointment.status,::text)}")
                    Text("${text("date")}: ${date(d.appointment.startAt)}"); Text("${text("service")}: ${value(d.service?.name)}")
                    Text("${text("resource")}: ${if (d.resource?.id == null) text("notAvailable") else value(d.resource.name)}")
                    Text("${text("notes")}: ${value(d.notes)}")
                }
            }
        }
    }
}
