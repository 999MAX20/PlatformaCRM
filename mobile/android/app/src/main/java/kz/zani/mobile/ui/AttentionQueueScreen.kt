package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun AttentionQueueScreen(agenda: AgendaViewModel, model: AttentionQueueViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun error(p: ReadProblem) = text(when (p) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })
    fun kind(item: AttentionItem) = text(when (item.readTarget?.kind) { AttentionKind.TASK -> "tasks"; AttentionKind.CONVERSATION -> "inbox"; AttentionKind.APPOINTMENT -> "appointments"; null -> "notAvailable" })
    val scope = agenda.state.selection; val business = scope?.business?.id; val state = model.state; val epoch=agenda.state.businessEpoch;val current = state.business == business && state.scopeEpoch==epoch
    fun ownsAgenda()=agenda.state.selection?.business?.id==business && agenda.state.businessEpoch==epoch
    val control=if(current)model.control else null
    fun ownsControl()=control!=null && model.matches(control) && agenda.state.selection?.business?.id==control.business && agenda.state.businessEpoch==control.epoch
    var menu by remember { mutableStateOf(false) }
    val scroll = rememberLazyListState()
    val readScope=text("attention");val bootstrapScope=readScope+": "+text("business");val detailScope=readScope+": "+text("details")
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    val loading = Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val detailProgress = Modifier.semantics { contentDescription = detailScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    LaunchedEffect(business,epoch) {if(ownsAgenda()) {if(!current || (!state.loaded && !state.loading && state.problem == null))model.load(business,epoch);if(!current)scroll.scrollToItem(0)}}
    BackHandler(enabled = current && state.selectedID != null, onBack = {if(ownsControl())model.back(control)})
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("attention"), style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall); Text(text("readOnly"), style = MaterialTheme.typography.labelSmall)
        if (scope != null) Box {
            OutlinedButton(onClick = { menu = true }) { Text(scope.business.name) }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==scope.business.id},text = { Text(member.name) }, onClick = { menu=false;if(ownsAgenda())agenda.load(member.id,scope.day) }) }
            }
        }
        when {
            business == null && agenda.state.problem != null -> { Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)}); Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) } }
            business == null || !current || state.loading -> CircularProgressIndicator(loading)
            state.selectedID != null -> {
                TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick = {if(ownsControl())model.back(control)}) { Text(text("back")) }
                when {
                    state.detailLoading -> CircularProgressIndicator(detailProgress)
                    state.detailProblem != null -> { Text(error(state.detailProblem), modifier = announcement.semantics {contentDescription=detailScope+": "+error(state.detailProblem)}); Button(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("retry")},onClick = {if(ownsControl())model.retryDetail(control)}) { Text(text("retry")) } }
                    state.detail != null -> AttentionTargetContent(state.detail, scope?.business?.timezone, language, copy, Modifier.weight(1f))
                }
            }
            else -> {
                OutlinedTextField(value = state.query, onValueChange = {if(ownsControl())model.search(it,control)}, label = { Text(text("inboxSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                if (state.problem != null) Text(error(state.problem), modifier = announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
                else if (state.loaded) {
                    Text("${text("list")}: ${state.items.size} · ${text("windowLimit")}: ${state.limit}", style = MaterialTheme.typography.labelSmall)
                    if (state.windowCapped) Text(text("partial"), modifier = announcement)
                    if (state.showsEmpty) Text(text("noResults"), modifier = announcement)
                    LazyColumn(Modifier.weight(1f), state = scroll) {
                        items(state.visible, key = { it.stableKey }) { item ->
                            val row = if (item.readTarget != null) Modifier.clickable(role = Role.Button) {if(ownsControl())model.open(item.identity,control)} else Modifier
                            ListItem(headlineContent = { Text(value(item.entity.title)) }, supportingContent = { Column { Text(kind(item)); Text("${text("openTarget")}: ${text(if (item.readTarget == null) "notAvailable" else "readOnly")}") } }, modifier = row)
                        }
                    }
                }
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {if(ownsControl())model.retryList(control)}) { Text(text("retry")) }
            }
        }
    }
}
