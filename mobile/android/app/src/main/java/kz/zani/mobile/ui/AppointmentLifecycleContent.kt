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

@Composable fun AppointmentLifecycleContent(model:AppointmentLifecycleModel,copy:Map<String,String>,isCurrent:()->Boolean,prepare:(AppointmentLifecycleAction,AppointmentLifecycleControl)->Unit) {
    fun text(k:String)=copy[k] ?: k
    fun action(a:AppointmentLifecycleAction)=text(when(a) {AppointmentLifecycleAction.CONFIRM->"appointmentLifecycleConfirm";AppointmentLifecycleAction.CANCEL->"appointmentLifecycleCancel";AppointmentLifecycleAction.RESCHEDULE->"appointmentLifecycleReschedule";AppointmentLifecycleAction.COMPLETE->"appointmentLifecycleComplete";AppointmentLifecycleAction.NO_SHOW->"appointmentLifecycleNoShow"})
    val scope=rememberCoroutineScope();val control=model.control
    if(isCurrent() && model.canPresent && control!=null)Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("appointmentLifecycle"),style=MaterialTheme.typography.titleSmall);Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
        val record=model.submission;val review=model.review
        if(model.blocked) {
            if(record==null)Text(text("taskCommentFakeQuarantined"))
            else {
                Text(action(record.attempt.review.action));Text(record.attempt.review.source.appointment.title ?: text("notAvailable"))
                record.attempt.review.reschedule?.let {AppointmentRescheduleSummary(it,copy)}
                record.terminalReceipt?.let {Text("${text("status")}: ${AppointmentStatusText.label(it.status,::text)}");Text(text("appointmentTerminalLimits"))}
                Text(text(when(record.phase){AppointmentLifecyclePhase.PENDING->"taskCommentFakePending";AppointmentLifecyclePhase.ACCEPTED_FIXTURE->"appointmentLifecycleAccepted";AppointmentLifecyclePhase.REJECTED_FIXTURE->"appointmentLifecycleRejected";AppointmentLifecyclePhase.UNKNOWN->"appointmentLifecycleUnknown"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                record.receipt?.let {Text("${text("status")}: ${AppointmentStatusText.label(it.appointment.status,::text)}");if(it.replayed)Text(text("appointmentLifecycleReplay"))}
                if(record.receipt!=null && record.attempt.review.reschedule!=null) {Text("${text("intervalStart")}: ${record.receipt.appointment.startAt}");Text(text("appointmentRescheduleReceiptLimits"))}
                if(record.phase in listOf(AppointmentLifecyclePhase.ACCEPTED_FIXTURE,AppointmentLifecyclePhase.REJECTED_FIXTURE))TextButton(modifier=Modifier.semantics {contentDescription=text("appointmentLifecycle")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
            }
        } else if(review!=null) {
            Text(text("appointmentLifecycleReview"));Text(action(review.action));Text(review.source.appointment.title ?: text("notAvailable"));Text("${text("business")}: ${review.source.read.scope.business.name}")
            review.reschedule?.let {AppointmentRescheduleSummary(it,copy);Text(text("appointmentRescheduleReceiptLimits"))}
            if(review.action.isGenericTerminal)Text(text("appointmentTerminalLimits"))
            Button(onClick={scope.launch {if(isCurrent())model.submit(control)}}) {Text(text("appointmentLifecycleSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("appointmentLifecycle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
        } else if(model.reschedulePresented)AppointmentRescheduleFields(model,copy,isCurrent) else AppointmentLifecycleAction.entries.forEach {value->if(model.canPrepare(value))Button(onClick={if(isCurrent())prepare(value,control)}) {Text(action(value))}}
    }
}

@Composable private fun AppointmentRescheduleSummary(input:AppointmentRescheduleInput,copy:Map<String,String>) {
    fun text(k:String)=copy[k] ?: k
    Text("${text("appointmentRescheduleTime")}: ${input.start.raw}")
    Text("${text("resource")}: ${when(val r=input.resource) {AppointmentRescheduleResource.Clear->text("appointmentRescheduleClear");is AppointmentRescheduleResource.Linked->r.detail.name}}")
    if(input.reason.isNotEmpty())Text("${text("appointmentRescheduleReason")}: ${input.reason}")
}
@Composable private fun AppointmentRescheduleFields(model:AppointmentLifecycleModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(k:String)=copy[k] ?: k
    val scope=rememberCoroutineScope();val control=model.control ?: return;val input=model.inputControl
    Text(text("appointmentRescheduleTimeHint"))
    key(input?.visit) {
        OutlinedTextField(value=model.rawStart,onValueChange={if(isCurrent())model.setStart(it,input)},label={Text(text("appointmentRescheduleTime"))},enabled=model.editingReschedule,isError=model.rawStart.isNotEmpty() && !model.timeInputValid,supportingText={if(model.rawStart.isNotEmpty() && !model.timeInputValid)Text(text("appointmentRescheduleTimeInvalid"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})
        OutlinedTextField(value=model.rawReason,onValueChange={if(isCurrent())model.setReason(it,input)},label={Text(text("appointmentRescheduleReason"))},enabled=model.editingReschedule)
    }
    if(model.resourceLoading)CircularProgressIndicator()
    model.resourceFailure?.let {Text(text(when(it) {ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notFound";else->"unavailable"}),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})}
    val resource=model.resourceChoice
    Text(when(resource) {null->text("appointmentRescheduleChoice");AppointmentRescheduleResource.Clear->text("appointmentRescheduleClear");is AppointmentRescheduleResource.Linked->resource.detail.name})
    TextButton(enabled=model.editingReschedule,onClick={if(isCurrent())model.chooseClear(control)}) {Text(text("appointmentRescheduleClear"))}
    if(model.linkedResourceAvailable)TextButton(enabled=model.editingReschedule,onClick={scope.launch {if(isCurrent())model.loadLinkedResource(control)}}) {Text(text("appointmentRescheduleLinked"))}
    Button(enabled=model.canReviewReschedule,onClick={if(isCurrent())model.reviewReschedule(control)}) {Text(text("appointmentRescheduleReview"))}
    TextButton(modifier=Modifier.semantics {contentDescription=text("appointmentLifecycle")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}
}
