package kz.zani.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun AgendaScreen(model: AgendaViewModel, copy: Map<String, String>, language: String) {
    fun text(key: String) = copy[key] ?: key
    fun error(problem: ReadProblem) = text(when (problem) { ReadProblem.DENIED -> "denied"; ReadProblem.NOT_FOUND -> "notFound"; else -> "unavailable" })
    val state = model.state
    val control=model.control
    val resources=model.resources
    val resourcePresentation=resources?.presentation
    val services=model.services
    val servicePresentation=services?.presentation
    val listScroll = rememberLazyListState()
    val dayScroll = rememberLazyListState()
    val detailScroll = rememberScrollState()
    val relations = model.relations
    val relationControl=relations?.presentation
    val workReturn=relations?.profile?.workReturnControl
    val childOpen = relations?.state?.request?.scope == state.selection && relations?.state?.request?.id == state.detailID && relations?.state?.selected != null
    fun back() {if(!model.matches(control))return;if(childOpen) {if(relations?.matches(relationControl)==true && relations.profile.backWork(workReturn)==ClientWorkBack.NO_CHILD)relations.back(relationControl)} else model.back(control)}
    var businessMenu by remember { mutableStateOf(false) }
    var showDate by remember {mutableStateOf(false)}
    var dateOwner by remember {mutableStateOf<AgendaControl?>(null)}
    var dateVisit by remember {mutableIntStateOf(0)}
    val selectedDay = state.selection?.day
    val readScope=text("appointments");val detailScope=readScope+": "+text("details")
    val loadingStatus = Modifier.semantics {
        contentDescription = readScope+": "+text("loading")
        liveRegion = LiveRegionMode.Polite
    }
    val detailLoadingStatus = Modifier.semantics {
        contentDescription = detailScope+": "+text("loading")
        liveRegion = LiveRegionMode.Polite
    }
    val statusAnnouncement = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
    BackHandler(enabled = state.detailID != null, onBack = ::back)
    LaunchedEffect(Unit) { model.start() }
    LaunchedEffect(state.selection?.business?.id, selectedDay) {
        showDate = false; listScroll.scrollToItem(0); dayScroll.scrollToItem(0)
    }
    LaunchedEffect(state.selection) {showDate=false;dateOwner=null;++dateVisit}
    LaunchedEffect(state.detailID) { detailScroll.scrollTo(0) }
    Column(Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text("fixtureMode"), style = MaterialTheme.typography.labelSmall)
        if(resources?.presented==true) {ResourceDirectoryContent(resources,copy,onClose={model.closeResources(resourcePresentation)})}
        else if(services?.presented==true) {ServiceDirectoryContent(services,copy,onClose={model.closeServices(servicePresentation)})}
        else if (state.detailID != null) {
            TextButton(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("back")},onClick = ::back) { Text(text("back")) }
            Text(text("details"), style = MaterialTheme.typography.titleLarge)
            if (childOpen && relations != null) AppointmentRelatedContent(relations,copy,language,Modifier.weight(1f),isCurrent={model.matches(control) && relations.matches(relationControl) && relations.state.request==control.detail},bookingBridge={slot,review->model.bookingCandidateControl(control,relationControl,slot,review)},useBookingCandidate={model.useBookingCandidate(it)})
            else Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(detailScroll), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                when {
                    state.detailLoading -> CircularProgressIndicator(modifier = detailLoadingStatus)
                    state.detailProblem != null -> { Text(error(state.detailProblem), modifier = statusAnnouncement.semantics {contentDescription=detailScope+": "+error(state.detailProblem)}); Button(modifier=Modifier.semantics {contentDescription=detailScope+": "+text("retry")},onClick = {model.retryDetail(control)}) { Text(text("retry")) } }
                    state.detail != null -> {
                        val detail = state.detail
                        Text(detail.appointment.title ?: text("notAvailable"))
                        Text("${text("status")}: ${AppointmentStatusText.label(detail.appointment.status,::text)}")
                        Text("${text("intervalStart")}: ${formatAgendaEndpoint(detail.appointment.startAt, state.selection?.business?.timezone, language) ?: text("notAvailable")}")
                        Text("${text("intervalEnd")}: ${formatAgendaEndpoint(detail.appointment.endAt, state.selection?.business?.timezone, language) ?: text("notAvailable")}")
                        state.selection?.let { scope ->
                            Text("${text("timeZone")}: ${scope.business.timezone}")
                            AgendaDayDisplay(listOf(detail.appointment),scope.day,scope.day,scope.business.timezone).sourceRows.firstOrNull()?.issue?.let { Text(text(it.key), modifier = statusAnnouncement) }
                        }
                        Text("${text("service")}: ${detail.service?.name ?: text("notAvailable")}")
                        Text("${text("resource")}: ${if (detail.resource?.id == null) text("notAvailable") else detail.resource?.name ?: text("notAvailable")}")
                        detail.notes?.takeIf { it.isNotBlank() }?.let { Text("${text("notes")}: $it") }
                        model.booking?.let {booking->model.bookingEntryControl?.let {entry->AppointmentBookingContent(booking,copy,isCurrent={model.matchesBookingEntry(entry)},open={child->model.openBooking(entry,child)},back={child->model.backBooking(entry,child)},acknowledge={child,record->model.acknowledgeBooking(entry,child,record)})}}
                        model.lifecycle?.let {lifecycle->model.lifecycleEntryControl?.let {entry->AppointmentLifecycleContent(lifecycle,copy,isCurrent={model.matchesLifecycleEntry(entry)},prepare={action,child->model.prepareLifecycle(action,entry,child)})}}
                        if (relations != null && model.booking?.presented!=true) {
                            val expected = relations.state.request
                            AppointmentRelationLinks(relations,copy,isCurrent={model.matches(control) && relations.state.request==control.detail}) {
                                if(expected!=null && relations.state.request==expected && model.state.selection==expected.scope && model.state.detailID==expected.id)model.retryDetail(control)
                            }
                        }
                    }
                }
            }
        } else {
            Text(text("appointments"), style = MaterialTheme.typography.titleLarge)
            model.serviceEntry?.let {entry->val child=services?.control;Button(onClick={model.openServices(entry,child)}) {Text(text("services"))}}
            model.resourceEntry?.let {entry->val child=resources?.control;Button(onClick={model.openResources(entry,child)}) {Text(text("resources"))}}
            Box {
                OutlinedButton(onClick = { businessMenu = true }) { Text(state.selection?.business?.name ?: text("business")) }
                DropdownMenu(expanded = businessMenu, onDismissRequest = { businessMenu = false }) {
                    state.businesses.forEach { business -> DropdownMenuItem(modifier=Modifier.semantics {selected=business.id==state.selection?.business?.id},text = { Text(business.name) }, onClick = { businessMenu=false;model.switchBusiness(business.id,control) }) }
                }
            }
            if (selectedDay != null) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = state.mode == AgendaMode.LIST, onClick = {model.setMode(AgendaMode.LIST,state.mode,control)}, label = { Text(text("list")) })
                FilterChip(selected = state.mode == AgendaMode.CALENDAR, onClick = {model.setMode(AgendaMode.CALENDAR,state.mode,control)}, label = { Text(text("calendar")) })
            }
            TextButton(onClick = {if(model.matches(control)) {dateOwner=control;++dateVisit;showDate=true}}) { Text("${text("date")}: $selectedDay") }
            Text("${text("timeZone")}: ${state.selection?.business?.timezone}", style = MaterialTheme.typography.labelSmall)
            if(showDate && model.matches(dateOwner)) {
                val expectedDate=dateOwner
                val visit=dateVisit
                fun closeDate() {if(dateOwner==expectedDate && dateVisit==visit) {showDate=false;dateOwner=null;++dateVisit}}
                val picker = rememberDatePickerState(initialSelectedDateMillis = LocalDate.parse(selectedDay).atStartOfDay().toInstant(ZoneOffset.UTC).toEpochMilli())
                DatePickerDialog(onDismissRequest = {closeDate()}, confirmButton = {
                    TextButton(onClick = {
                        if(dateVisit==visit && dateOwner==expectedDate && model.matches(expectedDate))picker.selectedDateMillis?.let {millis->expectedDate?.selection?.day?.let {previous->model.changeDay(Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate().toString(),previous,expectedDate)}}
                        closeDate()
                    }) { Text(text("calendar")) }
                }, dismissButton = {
                    TextButton(modifier=Modifier.semantics {contentDescription=text("appointments")+": "+text("date")+": "+text("back")},onClick = {closeDate()}) { Text(text("back")) }
                }) { DatePicker(state = picker, showModeToggle = false) }
            }
            }
            when {
                state.loading -> CircularProgressIndicator(modifier = loadingStatus)
                state.problem != null -> { Text(error(state.problem), modifier = statusAnnouncement.semantics {contentDescription=readScope+": "+error(state.problem)}); Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {model.retryList(control)}) { Text(text("retry")) } }
                else -> {
                    if (state.responseDay != null && state.responseDay != state.selection?.day) {
                        Text(text("agendaSourceDayMismatch"), modifier = statusAnnouncement)
                        Text("${text("date")}: ${state.responseDay}", style = MaterialTheme.typography.labelSmall)
                    }
                    if (state.partial) Text(text("partial"), modifier = statusAnnouncement)
                    val mismatched = state.responseDay != null && state.responseDay != state.selection?.day
                    if (state.partial || mismatched) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {model.retryList(control)}) { Text(text("retry")) }
                    if (state.items.isEmpty() && state.selection != null) {
                        if (state.showsEmptyResult) Text(text("empty"), modifier = statusAnnouncement)
                        if (!state.partial && !mismatched) TextButton(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick = {model.retryList(control)}) { Text(text("retry")) }
                    }
                    state.selection?.let { scope ->
                        AgendaDayContent(AgendaDayDisplay(state.items, scope.day, state.responseDay, scope.business.timezone), state.mode, scope.business.timezone, language, copy, if (state.mode == AgendaMode.CALENDAR) dayScroll else listScroll, Modifier.weight(1f),{model.openDetail(it,control)})
                    }
                }
            }
        }
    }
}
