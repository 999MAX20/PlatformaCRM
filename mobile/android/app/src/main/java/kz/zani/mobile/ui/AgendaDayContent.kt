package kz.zani.mobile.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun AgendaDayContent(display: AgendaDayDisplay, mode: AgendaMode, timezone: String, language: String, copy: Map<String,String>, scroll: LazyListState, modifier: Modifier, onOpen: (Int) -> Unit) {
    fun text(key: String) = copy[key] ?: key
    LazyColumn(modifier, state = scroll, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (mode == AgendaMode.CALENDAR) {
            if (display.scheduled.isNotEmpty()) {
                item { Text(text("dayAgenda"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() }) }
                items(display.scheduled, key = { it.appointment.id }) { row -> AgendaDayRowContent(row,mode,timezone,language,copy,onOpen) }
            }
            if (display.uncertain.isNotEmpty()) {
                item { Text(text("attention"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() }) }
                items(display.uncertain, key = { it.appointment.id }) { row -> AgendaDayRowContent(row,mode,timezone,language,copy,onOpen) }
            }
        } else items(display.sourceRows, key = { it.appointment.id }) { row -> AgendaDayRowContent(row,mode,timezone,language,copy,onOpen) }
    }
}
@Composable private fun AgendaDayRowContent(row: AgendaDayRow, mode: AgendaMode, timezone: String, language: String, copy: Map<String,String>, onOpen: (Int) -> Unit) {
    fun text(key: String) = copy[key] ?: key
    fun endpoint(raw: String?) = formatAgendaEndpoint(raw,timezone,language) ?: text("notAvailable")
    @Composable fun endpoints() {
        Text("${text("intervalStart")}: ${endpoint(row.appointment.startAt)}", style = MaterialTheme.typography.labelMedium)
        Text("${text("intervalEnd")}: ${endpoint(row.appointment.endAt)}", style = MaterialTheme.typography.labelMedium)
    }
    Column(Modifier.fillMaxWidth().clickable(role = Role.Button) { onOpen(row.appointment.id) }.semantics(mergeDescendants = true) {}.padding(vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (mode == AgendaMode.CALENDAR) endpoints()
        Text(row.appointment.title?.takeIf { it.isNotBlank() } ?: text("notAvailable"), style = MaterialTheme.typography.titleMedium)
        if (mode == AgendaMode.LIST) endpoints()
        Text("${text("status")}: ${AppointmentStatusText.label(row.appointment.status,::text)}", style = MaterialTheme.typography.labelSmall)
        Text("${text("resource")}: ${text("notAvailable")}", style = MaterialTheme.typography.labelSmall)
        row.issue?.let { Text(text(it.key), style = MaterialTheme.typography.labelSmall) }
    }
}
