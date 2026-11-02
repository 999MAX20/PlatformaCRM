package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*
import kz.zani.mobile.BuildConfig

@Composable fun NotificationCenterScreen(agenda: AgendaViewModel, model: NotificationCenterViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun category(raw: String?) = when (raw) { null -> text("all"); "sales" -> text("categorySales"); "finance" -> text("categoryFinance"); "system" -> text("categorySystem"); "ai_alerts" -> text("categoryAi"); "outreach" -> text("categoryOutreach"); "tasks" -> text("categoryTasks"); else -> value(raw) }
    fun error(problem: ReadProblem) = text(when (problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })
    fun marker(item: CRMNotification) = text(if (!item.readMarkerPresent) "notAvailable" else if (item.unread) "unread" else "notificationRead")
    val scope = agenda.state.selection; val business = scope?.business?.id; val state = model.state; val current = state.business == business && state.scopeEpoch==agenda.state.businessEpoch
    val control=model.control;val routeControl=model.routeControl;val ownerEpoch=agenda.state.businessEpoch
    fun ownsControl()=control!=null && model.matches(control) && agenda.state.selection?.business?.id==control.business && agenda.state.businessEpoch==control.epoch
    fun capturedBack() {if(ownsControl()) {if(routeControl!=null)model.backRoute(routeControl) else model.back(control)}}
    var businessMenu by remember { mutableStateOf(false) }; var categoryMenu by remember { mutableStateOf(false) }
    val readScope=text("notifications");val bootstrapScope=readScope+": "+text("business");val targetScope=readScope+": "+text("appointments")+": "+text("details")
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    val loading = Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val targetProgress = Modifier.semantics { contentDescription = targetScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    fun date(raw: String?) = raw?.let { formatAppointmentDate(it, scope?.business?.timezone, language) } ?: text("notAvailable")
    LaunchedEffect(business,ownerEpoch) {if(agenda.state.selection?.business?.id==business && agenda.state.businessEpoch==ownerEpoch && (!current || (!state.loaded && !state.loading && state.problem==null)))model.load(business,ownerEpoch)}
    BackHandler(enabled = current && state.selectedID != null, onBack = {capturedBack()})
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
        Text(text("notifications"), style = MaterialTheme.typography.titleLarge)
        if (scope != null) Box {
            OutlinedButton(onClick = { businessMenu = true }) { Text(scope.business.name) }
            DropdownMenu(expanded = businessMenu, onDismissRequest = { businessMenu = false }) {
                agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==scope.business.id},text = { Text(member.name) }, onClick = { businessMenu = false; agenda.load(member.id, scope.day) }) }
            }
        }
        when {
            business == null && agenda.state.problem != null -> { Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)}); Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) } }
            business == null || !current || state.loading -> CircularProgressIndicator(loading)
            state.selected != null -> {
                val selected = state.selected!!
                TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick = {capturedBack()}) { Text(text("back")) }
                if (state.targetActive) {
                    when {
                        state.targetLoading -> CircularProgressIndicator(targetProgress)
                        state.targetProblem != null -> { Text(error(state.targetProblem), modifier = announcement.semantics {contentDescription=targetScope+": "+error(state.targetProblem)}); Button(modifier=Modifier.semantics {contentDescription=targetScope+": "+text("retry")},onClick = {if(ownsControl())model.openTarget(control)}) { Text(text("retry")) } }
                        state.target != null -> {
                            val detail = state.target
                            LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                item { Text(value(detail.appointment.title)); Text("${text("status")}: ${AppointmentStatusText.label(detail.appointment.status,::text)}") }
                                item { Text("${text("date")}: ${date(detail.appointment.startAt)}") }
                                item { Text("${text("service")}: ${value(detail.service?.name)}") }
                                item { Text("${text("resource")}: ${if (detail.resource?.id == null) text("notAvailable") else value(detail.resource.name)}") }
                                detail.notes?.takeIf { it.isNotBlank() }?.let { notes -> item { Text("${text("notes")}: $notes") } }
                            }
                        }
                    }
                } else if (BuildConfig.DEBUG && model.routeEditorActive) {
                    val captured=model.routeControl
                    fun ownsRoute()=captured!=null && ownsControl() && model.matchesRoute(captured)
                    Text(text("relativeRouteCheck"),style=MaterialTheme.typography.titleMedium)
                    if(model.routeReviewing) {
                        Text(model.routeInput)
                        Text(text(if(model.routeCandidate==null)"relativeRouteUnsupported" else if(model.routeCorroborated)"relativeRouteMatched" else "relativeRouteUntrusted"),modifier=announcement)
                    } else {
                        OutlinedTextField(value=model.routeInput,onValueChange={if(ownsRoute())model.editRoute(it,captured)},label={Text(text("relativeRouteInput"))},modifier=Modifier.fillMaxWidth(),singleLine=true)
                        Button(onClick={if(ownsRoute())model.reviewRoute(captured)}) {Text(text("relativeRouteReview"))}
                    }
                } else {
                    LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        item { Text(value(selected.text)); Text(category(selected.category)); Text(marker(selected)) }
                        item { Text("${text("status")}: ${NotificationStatusText.label(selected.status,::text)}"); Text("${text("channel")}: ${ReadChannelText.label(selected.channel,::text)}") }
                        if(BuildConfig.DEBUG) item {TextButton(onClick={if(ownsControl())model.beginRoute(control)}) {Text(text("relativeRouteCheck"))}}
                        item {NotificationMarkReadContent(model.markRead,copy,isCurrent={ownsControl()})}
                        item {NotificationMarkUnreadContent(model.markUnread,copy,isCurrent={ownsControl()})}
                        if (selected.appointmentTarget != null) item { Button(onClick = {if(ownsControl())model.openTarget(control)}) { Text("${text("openTarget")} · ${text("appointments")}") } }
                    }
                }
            }
            else -> {
                OutlinedTextField(value = state.query, onValueChange = {if(ownsControl())model.search(it,control)}, label = { Text(text("inboxSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = state.unreadOnly, onClick = { if(ownsControl())model.filterUnread(!state.unreadOnly,state.unreadOnly,control) }, label = { Text(text("unread")) })
                    Box {
                        OutlinedButton(onClick = { categoryMenu = true }) { Text(category(state.category)) }
                        DropdownMenu(expanded = categoryMenu, onDismissRequest = { categoryMenu = false }) {
                            (listOf<String?>(null) + state.categories).forEach { option -> DropdownMenuItem(modifier=Modifier.semantics {selected=option==state.category},text = { Text(category(option)) }, onClick = { categoryMenu = false; if(ownsControl())model.filterCategory(option,state.category,control) }) }
                        }
                    }
                }
                if (state.problem != null) { Text(error(state.problem), modifier = announcement.semantics {contentDescription=readScope+": "+error(state.problem)}); Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryList(control) }) { Text(text("retry")) } }
                else {
                    if (state.partial) Text(text("partial"), modifier = announcement)
                    if (state.showsEmpty) Text(text(if (state.query.isBlank() && state.category == null && !state.unreadOnly) "notificationsEmpty" else "noResults"), modifier = announcement)
                    if (state.visible.isEmpty()) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryList(control) }) { Text(text("retry")) }
                    LazyColumn(Modifier.weight(1f)) {
                        items(state.visible, key = { it.id }) { item ->
                            ListItem(headlineContent = { Text(value(item.text)) }, supportingContent = { Text("${category(item.category)} · ${marker(item)}") }, modifier = Modifier.clickable(role = Role.Button) { if(ownsControl())model.open(item.id,control) })
                        }
                    }
                }
            }
        }
    }
}
