package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun HomeTodayScreen(agenda: AgendaViewModel, model: HomeTodayViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun count(n: Int?) = n?.toString() ?: text("notAvailable")
    fun error(p: ReadProblem) = text(if (p == ReadProblem.DENIED) "denied" else "unavailable")
    val scope=agenda.state.selection
    val business = scope?.business
    val epoch=agenda.state.businessEpoch
    fun ownsAgenda()=agenda.state.selection?.business?.id==business?.id && agenda.state.businessEpoch==epoch
    val state = model.state
    val homeControl=model.homeControl;val todayControl=model.todayControl;val navigation=model.navigationControl
    val homeScope=text("home");val bootstrapScope=homeScope+": "+text("business");val todayScope=homeScope+": "+text("today")
    fun owns(owner:HomeOwnerControl?)=owner!=null && model.owner==owner && agenda.state.selection?.business?.id==owner.business && agenda.state.businessEpoch==owner.epoch
    var menu by remember { mutableStateOf(false) }
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    LaunchedEffect(business?.id,epoch) {if(business!=null && ownsAgenda())model.start(business.id,model.day(business.timezone),epoch)}
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Text(text("home"), style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
            if (business != null) Box {
                OutlinedButton(onClick = { menu = true }) { Text(business.name) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==business.id},text = { Text(member.name) }, onClick = { menu=false;if(ownsAgenda() && scope!=null)agenda.load(member.id,scope.day) }) }
                }
            } else if (agenda.state.problem != null) {
                Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)}); Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) }
            } else Text(text("loading"), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+text("loading")})
        }
        if (business != null && state.business == business.id && state.scopeEpoch==agenda.state.businessEpoch) {
            item {
                if (state.homeLoading) Text(text("loading"), modifier = announcement.semantics {contentDescription=homeScope+": "+text("loading")})
                else if (state.homeProblem != null) Text(error(state.homeProblem), modifier = announcement.semantics {contentDescription=homeScope+": "+error(state.homeProblem)})
                else state.home?.let { home ->
                    Text("${text("todayAppointments")}: ${count(home.appointments?.today)}")
                    Text("${text("openTasks")}: ${count(home.tasks?.open)}")
                    Text("${text("inbox")} · ${text("unread")}: ${count(home.conversations?.unread)}")
                }
                TextButton(modifier=Modifier.semantics {contentDescription=homeScope+": "+text("retry")},onClick = {if(owns(homeControl?.owner))model.reloadHome(homeControl)}, enabled = !state.homeLoading) { Text(text("retry")) }
            }
            item {
                Text(text("today"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
                Text("${text("date")}: ${state.day}")
                if (state.todayLoading) Text(text("loading"), modifier = announcement.semantics {contentDescription=todayScope+": "+text("loading")})
                else if (state.todayProblem != null) Text(error(state.todayProblem), modifier = announcement.semantics {contentDescription=todayScope+": "+error(state.todayProblem)})
            }
            if (!state.todayLoading && state.todayProblem == null && state.today != null) {
                val a = state.today.appointments; val t = state.today.tasks
                item {
                    Text("${text("appointments")}: ${count(a?.total)}")
                    if (a?.partial == true) Text(text("partial"), modifier = announcement)
                    if (a?.total == 0) Text(text("todayAppointmentsEmpty"), modifier = announcement)
                }
                items(a?.items ?: emptyList(), key = { "appointment/${it.id}" }) { appointment ->
                    Column(Modifier.semantics(mergeDescendants = true) {}) {
                        Text(value(appointment.title)); Text(formatAppointmentDate(appointment.startAt, business.timezone, language) ?: text("notAvailable"), style = MaterialTheme.typography.labelSmall)
                    }
                }
                item {
                    Text("${text("tasks")}: ${count(t?.total)}")
                    if (t?.partial == true) Text(text("partial"), modifier = announcement)
                    if (t?.total == 0) Text(text("todayTasksEmpty"), modifier = announcement)
                }
                items(t?.items ?: emptyList(), key = { "task/${it.id}" }) { task ->
                    Column(Modifier.semantics(mergeDescendants = true) {}) {
                        Text(value(task.title)); Text(task.dueAt?.let { formatAppointmentDate(it, business.timezone, language) } ?: text("notAvailable"), style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
            item { TextButton(modifier=Modifier.semantics {contentDescription=todayScope+": "+text("retry")},onClick = {if(owns(todayControl?.owner))model.reloadToday(todayControl)}, enabled = !state.todayLoading) { Text(text("retry")) } }
            items(HomeDestination.entries) { target -> OutlinedButton(onClick = {if(owns(navigation?.owner))model.open(target,navigation)}, modifier = Modifier.fillMaxWidth()) { Text(text(target.key)) } }
        }
    }
}
