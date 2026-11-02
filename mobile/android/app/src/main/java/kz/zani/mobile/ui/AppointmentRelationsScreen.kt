package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun AppointmentRelationLinks(links: AppointmentRelationsViewModel, copy: Map<String,String>,isCurrent:()->Boolean,onRetryParent: () -> Unit) {
    fun text(key: String) = copy[key] ?: key
    val state = links.state; val parent = state.parent; val request = state.request
    val presentation=links.presentation
    val parentScope=text("appointments")+": "+text("details")
    if(isCurrent() && presentation!=null && parent != null && request != null) {
        Text(text("senderClient"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
        if (parent.linkedClientID != null) TextButton(onClick = {if(isCurrent())links.openClient(presentation=presentation)}) { Text("${text("openTarget")} · ${text("senderClient")}") }
        else { Text(text("notAvailable")); if (parent.clientLinkAmbiguous) Text(text("attention"), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }) }
        AppointmentReferenceKind.entries.forEach {kind->if(links.referenceAvailable(kind))TextButton(onClick={if(isCurrent())links.openReference(kind,presentation)}) {Text(text("openTarget")+" · "+text(if(kind==AppointmentReferenceKind.SERVICE)"service" else "referenceResourceTitle"))}}
        Text(text("tasks"), style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
        if (state.tasks != null && parent.maxRelated != null) {
            Text("${text("list")}: ${state.tasks.size} · ${text("windowLimit")}: ${parent.maxRelated}", style = MaterialTheme.typography.labelSmall)
            if (state.tasks.size == parent.maxRelated) Text(text("partial"), modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            if (state.tasks.isEmpty()) Text(text("noResults"))
            state.tasks.forEach { task -> TextButton(onClick = {if(isCurrent())links.openTask(task.id,presentation=presentation)}) { Text(task.title?.takeIf { it.isNotBlank() } ?: text("notAvailable")) } }
        } else Text(text("notAvailable"))
        Button(modifier=Modifier.semantics {contentDescription=parentScope+": "+text("retry")},onClick = {if(isCurrent() && links.matches(presentation))onRetryParent()}) { Text(text("retry")) }
    }
}

@Composable fun AppointmentRelatedContent(links: AppointmentRelationsViewModel, copy: Map<String,String>, language: String, modifier: Modifier,isCurrent:()->Boolean,bookingBridge:((AppointmentSlotControl?,AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl?)?=null,useBookingCandidate:((AppointmentBookingCandidateControl)->Unit)?=null) {
    fun text(key: String) = copy[key] ?: key
    val state = links.state; val request = state.request ?: return
    val presentation=links.presentation
    if(!isCurrent() || !links.matches(presentation))return
    val taskScope=text("appointments")+": "+text("tasks")+": "+text("details")
    when (val target = state.selected) {
        is AppointmentRelatedTarget.Client -> ClientProfileContent(links.profile, request.scope.business.id, target.id, copy, request.scope.business.timezone, language, modifier, onContact = { _, _ -> }, onRetry={if(isCurrent())links.retry(presentation)},isCurrent={isCurrent() && links.matches(presentation)})
        is AppointmentRelatedTarget.Task -> Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            when {
                state.loading -> CircularProgressIndicator(Modifier.semantics { contentDescription = taskScope+": "+text("loading"); liveRegion = LiveRegionMode.Polite })
                state.problem != null -> {
                    Text(text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }), modifier = Modifier.semantics { contentDescription=taskScope+": "+text(when (state.problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notAvailable"; else -> "unavailable" }); liveRegion = LiveRegionMode.Polite })
                    Button(modifier=Modifier.semantics {contentDescription=taskScope+": "+text("retry")},onClick = {if(isCurrent())links.retry(presentation)}) { Text(text("retry")) }
                }
                state.task != null -> AttentionTargetContent(AttentionDetail.TaskRead(state.task), request.scope.business.timezone, language, copy, Modifier.weight(1f))
            }
        }
        is AppointmentRelatedTarget.Service,is AppointmentRelatedTarget.Resource -> target.referenceKind?.let {kind->AppointmentReferenceContent(links,kind,copy,modifier,language,isCurrent={isCurrent() && links.matches(presentation)},bookingBridge=bookingBridge,useBookingCandidate=useBookingCandidate)}
        null -> Unit
    }
}
