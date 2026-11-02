package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kz.zani.mobile.core.*

@Composable fun AppointmentBookingContent(model:AppointmentBookingModel,copy:Map<String,String>,isCurrent:()->Boolean,open:(AppointmentBookingControl?)->Unit,back:(AppointmentBookingControl?)->Unit,acknowledge:(AppointmentBookingControl?,AppointmentBookingRecord)->Unit) {
    fun text(k:String)=copy[k] ?: k
    val control=model.control;val scope=rememberCoroutineScope()
    if(isCurrent() && model.canPresent && control!=null)Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("bookingTitle"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
        val record=model.submission;val review=model.review
        if(model.blocked) {
            if(record==null)Text(text("taskCommentFakeQuarantined"))else {
                AppointmentBookingSummary(record.attempt.review.source,record.attempt.review.input,copy)
                Text(text(when(record.phase) {AppointmentBookingPhase.PENDING->"taskCommentFakePending";AppointmentBookingPhase.ACCEPTED_FIXTURE->"appointmentLifecycleAccepted";AppointmentBookingPhase.REJECTED_FIXTURE->"appointmentLifecycleRejected";AppointmentBookingPhase.UNKNOWN->"appointmentLifecycleUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                record.receipt?.let {Text("#${it.appointment.id}");Text("${text("status")}: ${AppointmentStatusText.label(it.appointment.status,::text)}");Text(text("bookingLimits"))}
                if(record.phase in listOf(AppointmentBookingPhase.ACCEPTED_FIXTURE,AppointmentBookingPhase.REJECTED_FIXTURE))TextButton(modifier=Modifier.semantics {contentDescription=text("bookingTitle")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
            }
        } else if(review!=null) {
            AppointmentBookingSummary(review.source,review.input,copy);Text(text("bookingLimits"))
            Button(onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("appointmentLifecycleSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("bookingTitle")+": "+text("back")},onClick={if(isCurrent())back(control)}) {Text(text("back"))}
        } else if(model.presented) {
            if(model.clientPickerOwner!=null)model.clientChoices?.let {AppointmentBookingClientPickerContent(model,it,copy,isCurrent)}
            else if(model.selector!=null)AppointmentBookingDirectoryContent(model,copy,isCurrent)
            else {
            val clientChild=model.clientChoices?.control
            if(model.clientChoices!=null)TextButton(enabled=model.editing,onClick={if(isCurrent())model.openClientPicker(control,clientChild)}) {Text(text("bookingSelectClient"))}
            val serviceChild=model.serviceChoices?.control;val resourceChild=model.resourceChoices?.control
            if(model.serviceChoices!=null)TextButton(enabled=model.editing,onClick={scope.launch {if(isCurrent())model.openSelector(AppointmentBookingDirectoryKind.SERVICE,control,serviceChild,resourceChild)}}) {Text(text("bookingSelectService"))}
            if(model.resourceChoices!=null)TextButton(enabled=model.editing,onClick={scope.launch {if(isCurrent())model.openSelector(AppointmentBookingDirectoryKind.RESOURCE,control,serviceChild,resourceChild)}}) {Text(text("bookingSelectResource"))}
            val input=model.inputControl;Text(text("appointmentRescheduleTimeHint"))
            key(input?.visit) {OutlinedTextField(value=model.rawStart,onValueChange={if(isCurrent())model.setStart(it,input)},label={Text(text("appointmentRescheduleTime"))},enabled=model.editing,isError=model.rawStart.isNotEmpty() && !model.timeValid,supportingText={if(model.rawStart.isNotEmpty() && !model.timeValid)Text(text("appointmentRescheduleTimeInvalid"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})}
            Text("${text("client")}: ${model.client?.title ?: text("notAvailable")}")
            TextButton(enabled=model.editing,onClick={scope.launch {if(isCurrent())model.load(AppointmentBookingReadKind.CLIENT,control)}}) {Text(text("bookingReadClient"))}
            Text("${text("service")}: ${model.service?.name ?: text("notAvailable")}")
            TextButton(enabled=model.editing,onClick={scope.launch {if(isCurrent())model.load(AppointmentBookingReadKind.SERVICE,control)}}) {Text(text("bookingReadService"))}
            Text(when(val r=model.resource) {null->text("appointmentRescheduleChoice");AppointmentRescheduleResource.Clear->text("appointmentRescheduleClear");is AppointmentRescheduleResource.Linked->r.detail.name})
            TextButton(enabled=model.editing,onClick={if(isCurrent())model.chooseClear(control)}) {Text(text("appointmentRescheduleClear"))}
            if(model.linkedResourceAvailable)TextButton(enabled=model.editing,onClick={scope.launch {if(isCurrent())model.load(AppointmentBookingReadKind.RESOURCE,control)}}) {Text(text("bookingReadResource"))}
            if(model.loading!=null)CircularProgressIndicator()
            model.failure?.let {Text(text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
            Button(enabled=model.canReview,onClick={if(isCurrent())model.prepareReview(control)}) {Text(text("bookingReview"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("bookingTitle")+": "+text("back")},onClick={if(isCurrent())back(control)}) {Text(text("back"))}
            }
        } else Button(enabled=model.canOpen,onClick={if(isCurrent())open(control)}) {Text(text("bookingOpen"))}
    }
}
@Composable private fun AppointmentBookingSummary(source:AppointmentBookingSource,input:AppointmentBookingInput,copy:Map<String,String>) {
    fun text(k:String)=copy[k] ?: k
    Text("${text("business")}: ${source.read.scope.business.name}")
    Text("${text("client")}: ${input.client.title ?: text("notAvailable")} · #${input.client.id}")
    Text("${text("service")}: ${input.service.name} · #${input.service.id}")
    Text("${text("resource")}: ${when(val r=input.resource) {AppointmentRescheduleResource.Clear->text("appointmentRescheduleClear");is AppointmentRescheduleResource.Linked->r.detail.name+" · #${r.detail.id}"}}")
    Text("${text("intervalStart")}: ${input.start.raw}")
}
