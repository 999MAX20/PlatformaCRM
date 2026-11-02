package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.AppointmentStatusText
import kz.zani.mobile.core.ReadProblem
import kz.zani.mobile.core.ClientContact
import kz.zani.mobile.core.ClientEditContext

@Composable fun ClientProfileContent(model: ClientProfileViewModel, business: Int, id: Int, copy: Map<String, String>, timezone: String?, language: String, modifier: Modifier, onContact: (Int, ClientContact) -> Unit, onRetry: (() -> Unit)? = null,isCurrent:()->Boolean) {
    fun text(key: String) = copy[key] ?: key
    fun value(raw: String?) = raw?.takeIf { it.isNotBlank() } ?: text("notAvailable")
    val state = model.state
    val read=model.readSelection
    val readScope=text("clients")+": "+text("details")
    val overlayVisit=model.localOverlayVisit
    val current=isCurrent() && state.business==business && state.id==id
    val edit=model.edit
    val editSelection=edit?.state?.selection
    val editContext=state.scopeEpoch?.let {ClientEditContext(business,id,it)}
    fun retry() {if(!isCurrent() || model.readSelection!=read || model.state.loading)return;if(onRetry!=null)onRetry() else model.retry(read,state.scopeEpoch,onContact)}
    val work = model.work
    val workState = work?.state
    val request = workState?.selection
    val presentation=work?.presentation
    fun ownsEdit()=isCurrent() && model.localOverlayVisit==overlayVisit && model.merge?.context==null && model.readSelection==read && model.work?.presentation==presentation && presentation?.target==null && model.state.detail!=null && !model.state.loading && model.state.problem==null
    if(current && edit!=null && editSelection!=null && editSelection.context==editContext && ownsEdit()) {ClientEditContent(edit,editSelection,copy,modifier,isCurrent={ownsEdit()});return}
    fun ownsWork()=model.localOverlayVisit==overlayVisit && model.merge?.context==null && edit?.state?.selection==null && edit?.confirmation==null && isCurrent() && model.readSelection==read && work?.state?.selection==read && model.state.detail!=null && !model.state.loading && model.state.problem==null && work?.matches(presentation)==true
    val child = current && request != null && request.business == business && request.id == id && workState?.selected != null && state.detail != null && request==read
    val scroll = rememberLazyListState()
    BackHandler(enabled = child, onBack = {if(ownsWork())work?.back(presentation=presentation)})
    val announcement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        when {
            !current || state.loading -> CircularProgressIndicator(Modifier.semantics { contentDescription = readScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite })
            state.problem != null -> {
                Text(text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }), modifier = announcement.semantics {contentDescription=readScope+": "+text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" })})
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { retry() }) { Text(text("retry")) }
            }
            child && work != null -> ClientWorkChildContent(work,copy,timezone,language,Modifier.fillMaxSize(),isCurrent={ownsWork()})
            state.detail != null -> {
                val profile = state.detail
                LazyColumn(state = scroll, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    if(edit!=null && editContext!=null)item {ClientEditEntry(edit,editContext,copy,isCurrent={ownsEdit()})}
                    item { Text("${text("clientName")}: ${value(profile.client.title)}"); Text("${text("clientPhone")}: ${value(profile.client.phone)}"); Text("${text("clientEmail")}: ${value(profile.client.email)}") }
                    item { Text("${text("notes")}: ${value(profile.notes)}") }
                    model.merge?.let {merge->item {ClientMergePreviewContent(model,merge,copy,isCurrent={current && model.readSelection==read})}}
                    if (work != null) clientWorkLinks(work,copy,timezone,language,isCurrent={ownsWork()})
                    if (work == null && profile.appointments.isNotEmpty()) item { Text(text("appointments"), style = MaterialTheme.typography.titleMedium); if (profile.historyCapped) Text(text("partial"), modifier = announcement) }
                    items(if (work == null) profile.appointments else emptyList(), key = { it.appointment.id }) { visit ->
                        Column {
                            Text(value(visit.appointment.title)); Text(AppointmentStatusText.label(visit.appointment.status,::text))
                            Text(formatAppointmentDate(visit.appointment.startAt, timezone, language) ?: text("notAvailable"), style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
            else -> Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = { retry() }) { Text(text("retry")) }
        }
    }
}
