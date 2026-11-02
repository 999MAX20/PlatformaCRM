package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.ReadProblem
import kz.zani.mobile.core.ClientDraftContext
import kz.zani.mobile.core.ClientSearchContext

@Composable fun ClientDirectoryScreen(agenda: AgendaViewModel, model: ClientDirectoryViewModel, profile: ClientProfileViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    fun error(problem: ReadProblem) = text(when (problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })
    val scope = agenda.state.selection
    val business = scope?.business?.id
    val state = model.state
    var menu by remember { mutableStateOf(false) }
    val control=model.control
    val list=model.listControl
    val readScope=text("clients");val bootstrapScope=readScope+": "+text("business")
    fun ownsControl()=model.matches(control) && control!=null && agenda.state.selection?.business?.id==control.business && agenda.state.businessEpoch==control.epoch
    val onContact:(Int,kz.zani.mobile.core.ClientContact)->Unit={b,c->if(ownsControl())model.refreshContact(b,c,control)}
    val profileRead=profile.readSelection
    val workReturn=profile.workReturnControl
    fun backProfile() {if(ownsControl() && profile.workReturnControl==workReturn && !profile.backMerge(workReturn) && !profile.backEdit(workReturn) && profile.backWork(workReturn)==ClientWorkBack.NO_CHILD && model.back(control))profile.clear()}
    val current = state.business == business && state.scopeEpoch == agenda.state.businessEpoch
    val serverSearch=model.serverSearch
    val searchSelection=serverSearch?.state?.selection?.takeIf {current && it.context==business?.let {id->ClientSearchContext(id,agenda.state.businessEpoch)}}
    val draftSelection=model.draft.state.selection
    val draftCurrent=current && draftSelection?.context==business?.let { ClientDraftContext(it,agenda.state.businessEpoch) }
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    LaunchedEffect(business, agenda.state.businessEpoch) {
        if (!current || (!state.loaded && !state.loading && state.problem == null)) model.load(business, agenda.state.businessEpoch)
    }
    LaunchedEffect(business, agenda.state.businessEpoch, state.selectedID, control?.generation) {
        if (ownsControl() && business != null && state.selectedID != null) profile.loadScoped(business,state.selectedID,agenda.state.businessEpoch,onContact) else if(current && state.selectedID==null)profile.clear()
    }
    BackHandler(enabled = current && state.selected != null, onBack = {backProfile()})
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
        Text(text("clients"), style = MaterialTheme.typography.titleLarge)
        if (scope != null) Box {
            OutlinedButton(onClick = { menu = true }) { Text(scope.business.name) }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                agenda.state.businesses.forEach { member ->
                    DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==scope.business.id},text = { Text(member.name) }, onClick = { menu = false; agenda.load(member.id, scope.day) })
                }
            }
        }
        when {
            business == null && agenda.state.problem != null -> {
                Text(error(agenda.state.problem!!), modifier = announcement.semantics {contentDescription=bootstrapScope+": "+error(agenda.state.problem!!)})
                Button(modifier=Modifier.semantics {contentDescription=bootstrapScope+": "+text("retry")},onClick = agenda::start) { Text(text("retry")) }
            }
            business == null || !current || state.loading -> CircularProgressIndicator(Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite })
            serverSearch!=null && searchSelection!=null -> ClientSearchContent(serverSearch,searchSelection,copy,scope?.business?.timezone,language,Modifier.weight(1f),isCurrent={ownsControl() && model.draft.control==null && model.state.selectedID==null && serverSearch.state.selection==searchSelection})
            draftCurrent && draftSelection != null -> ClientDraftContent(model.draft,draftSelection,copy,Modifier.weight(1f),isCurrent={ownsControl() && model.state.selectedID==null && model.serverSearch?.state?.selection==null})
            state.selected != null -> {
                TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("details")+": "+text("back")},onClick = {backProfile()}) { Text(text("back")) }
                ClientProfileContent(profile, business!!, state.selectedID!!, copy, scope?.business?.timezone, language, Modifier.weight(1f), onContact,onRetry={if(ownsControl())profile.retry(profileRead,control?.epoch,onContact)},isCurrent={ownsControl() && profile.readSelection==profileRead})
            }
            else -> {
                if(serverSearch!=null && business!=null) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("clientServerSearch")},onClick={if(ownsControl() && model.openSearchFromList(list))profile.clear()}) {Text(text("clientServerSearch"))}
                OutlinedTextField(value = state.query, onValueChange = {if(ownsControl())model.searchList(it,list)}, label = { Text(text("clientSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                if (state.problem != null) {
                    Text(error(state.problem), modifier = announcement.semantics {contentDescription=readScope+": "+error(state.problem)})
                    Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryList(list) }) { Text(text("retry")) }
                } else {
                    if(state.loaded && business!=null)ClientDraftEntry(model.draft,ClientDraftContext(business,agenda.state.businessEpoch),copy,isCurrent={ownsControl() && model.matchesList(list)},onOpen={entry->if(model.openDraftFromList(entry,list))profile.clear()})
                    if (state.partial) Text(text("partial"), modifier = announcement)
                    if (state.showsEmpty) Text(text(if (state.query.isBlank()) "clientsEmpty" else "noResults"), modifier = announcement)
                    if (state.visible.isEmpty()) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { if(ownsControl())model.retryList(list) }) { Text(text("retry")) }
                    LazyColumn(Modifier.weight(1f)) {
                        items(state.visible, key = { it.id }) { client ->
                            ListItem(headlineContent = { Text(value(client.title)) }, supportingContent = { Text("${text("clientPhone")}: ${value(client.phone)}") }, modifier = Modifier.clickable(role = Role.Button) { if(ownsControl() && model.openList(client.id,list))profile.clear() })
                        }
                    }
                }
            }
        }
    }
}
