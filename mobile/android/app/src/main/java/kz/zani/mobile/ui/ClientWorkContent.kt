package kz.zani.mobile.ui

import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

fun LazyListScope.clientWorkLinks(work: ClientWorkModel, copy: Map<String,String>, timezone: String?, language: String,isCurrent:()->Boolean) {
    val state=work.state;val presentation=work.presentation ?: return;val parent=state.parent ?: return
    if(!isCurrent())return
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    item(key = "work-tasks") {
        Column {
            Text(text("tasks"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
            if (state.tasks == null) Text(text("notAvailable")) else {
                ClientWorkWindow(state.tasks.size,parent.maxRelated,copy)
                state.tasks.forEach { row -> TextButton(onClick = {if(isCurrent())work.open(ClientWorkTarget.Task(row.id),presentation=presentation)}) { Text(value(row.title)) } }
            }
        }
    }
    item(key = "work-conversations") {
        Column {
            Text(text("inbox"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
            if (state.conversations == null) Text(text("notAvailable")) else {
                ClientWorkWindow(state.conversations.size,parent.maxRelated,copy)
                state.conversations.forEach { row -> TextButton(onClick = {if(isCurrent())work.open(ClientWorkTarget.Conversation(row.id),presentation=presentation)}) { Text(value(row.title)) } }
            }
        }
    }
    item(key = "work-appointments") {
        Column {
            Text(text("appointments"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
            if (state.appointments == null) Text(text("notAvailable")) else {
                ClientWorkWindow(state.appointments.size,parent.maxRelated,copy)
                state.appointments.forEach { row -> TextButton(onClick = {if(isCurrent())work.open(ClientWorkTarget.Appointment(row.id),presentation=presentation)}) {
                    Column { Text(value(row.title)); Text(AppointmentStatusText.label(row.status,::text)); Text(formatAppointmentDate(row.startAt,timezone,language) ?: text("notAvailable"), style = MaterialTheme.typography.labelSmall) }
                } }
            }
        }
    }
}

@Composable private fun ClientWorkWindow(count: Int, limit: Int, copy: Map<String,String>) {
    Text("${copy["list"]}: $count · ${copy["windowLimit"]}: $limit", style = MaterialTheme.typography.labelSmall)
    if (count == limit) Text(copy["partial"] ?: "partial", modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
}

@Composable fun ClientWorkChildContent(work: ClientWorkModel, copy: Map<String,String>, timezone: String?, language: String, modifier: Modifier,isCurrent:()->Boolean) {
    val state=work.state;val target=state.selected ?: return;val presentation=work.presentation ?: return
    if(!isCurrent())return
    fun text(key: String) = copy[key] ?: key
    val title = when(target) { is ClientWorkTarget.Task -> "tasks"; is ClientWorkTarget.Conversation -> "inbox"; is ClientWorkTarget.Appointment -> "appointments" }
    val readScope=text("clients")+": "+text(title)+": "+text("details")
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text(title), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
        when {
            state.loading -> CircularProgressIndicator(Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite })
            state.problem != null -> {
                Text(text(when(state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }), modifier = Modifier.semantics { contentDescription=readScope+": "+text(when(state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }); liveRegion = LiveRegionMode.Polite })
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {if(isCurrent())work.retry(presentation)}) { Text(text("retry")) }
            }
            state.detail != null -> AttentionTargetContent(state.detail,timezone,language,copy,Modifier.weight(1f))
        }
    }
}
