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

@Composable fun LoadedSearchScreen(agenda: AgendaViewModel, model: LoadedSearchViewModel, feed: LoadedSearchFeed, copy: Map<String,String>, language: String, openSource: (Int) -> Unit,isCurrentFeed:(LoadedSearchFeed)->Boolean) {
    fun text(key: String) = copy[key] ?: key
    val state = model.state;val epoch=agenda.state.businessEpoch
    val current=state.feed==feed && feed.business==agenda.state.selection?.business?.id && feed.epoch==epoch && isCurrentFeed(feed)
    val control=if(current)model.control else null
    val input=if(current)model.inputControl else null
    fun ownsInput()=input!=null && model.inputControl==input && input.feed.business==agenda.state.selection?.business?.id && input.feed.epoch==agenda.state.businessEpoch && isCurrentFeed(input.feed)
    fun ownsControl()=control!=null && model.matches(control) && control.feed.business==agenda.state.selection?.business?.id && control.feed.epoch==agenda.state.businessEpoch && isCurrentFeed(control.feed)
    val hit = state.selected; val business = agenda.state.selection?.business
    val workReturn=model.profile.workReturnControl
    val readScope=text("inboxSearch")+": "+text("searchLoadedOnly");val detailScope=readScope+": "+text("details")
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    val loading = Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    val detailProgress = Modifier.semantics { contentDescription = detailScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite }
    var menu by remember { mutableStateOf(false) }
    // Kept above the leaf branch, so Back preserves result scroll/query and source context.
    val listState = androidx.compose.foundation.lazy.rememberLazyListState()
    BackHandler(enabled = current && hit != null, onBack = {if(ownsControl() && model.profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)model.back(control)})
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("inboxSearch"), style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
        if (current && hit != null && business?.id == hit.identity.business) {
            TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick = {if(ownsControl() && model.profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)model.back(control)}) { Text(text("back")) }
            Text("${text(hit.identity.kind.key)} · #${hit.identity.id}")
            when {
                hit.identity.kind == LoadedSearchKind.CLIENTS -> ClientProfileContent(model.profile, business.id, hit.identity.id, copy, business.timezone, language, Modifier.weight(1f), onContact = { _, _ -> }, onRetry = {if(ownsControl())model.retry(control)},isCurrent={ownsControl()})
                state.loading -> CircularProgressIndicator(detailProgress)
                state.problem != null -> {
                    Text(text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }), modifier = announcement.semantics {contentDescription=detailScope+": "+text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })})
                    Button(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("retry")},onClick = { if(ownsControl())model.retry(control) }) { Text(text("retry")) }
                }
                state.detail != null -> AttentionTargetContent(state.detail, business.timezone, language, copy, Modifier.weight(1f))
            }
        } else {
            Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
            if (business != null) Box {
                OutlinedButton(onClick = { menu = true }) { Text(business.name) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    agenda.state.businesses.forEach { member -> DropdownMenuItem(modifier=Modifier.semantics {selected=member.id==business.id},text = { Text(member.name) }, onClick = { menu=false;if(agenda.state.selection?.business?.id==business.id && agenda.state.businessEpoch==epoch)agenda.state.selection?.day?.let {agenda.load(member.id,it)} }) }
                }
            }
            Text(text("searchLoadedOnly"), style = MaterialTheme.typography.labelSmall)
            OutlinedTextField(value = if(current)state.query else "", onValueChange = {if(ownsInput())model.searchInput(it,input)}, label = { Text(text("inboxSearch")) }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Text(text("searchOrder"), style = MaterialTheme.typography.labelSmall)
            if (!current) CircularProgressIndicator(loading) else LazyColumn(Modifier.weight(1f), state = listState, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                feed.sources.forEach { source ->
                    item(key = "coverage:${source.kind}") {
                        Column {
                            Text(text(source.kind.key), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
                            Text(text(state.coverage(source).key), modifier = announcement)
                            source.token?.day?.let { Text(it, style = MaterialTheme.typography.labelSmall) }
                            TextButton(onClick = {if(ownsControl())model.sourceTab(source.kind,control)?.let(openSource)}) { Text("${text("openTarget")} · ${text(source.kind.key)}") }
                        }
                    }
                    items(state.matches.filter { it.identity.kind == source.kind }, key = { "${it.identity.kind}:${it.identity.business}:${it.identity.id}" }) { result ->
                        ListItem(headlineContent = { Text(result.title) }, supportingContent = { Text("${text(result.identity.kind.key)} · #${result.identity.id}") }, modifier = Modifier.clickable(role = Role.Button) {if(ownsControl())model.open(result,control)})
                    }
                }
                if (state.showsNoMatches) item { Text(text("searchNoMatches"), modifier = announcement) }
            }
        }
    }
}
