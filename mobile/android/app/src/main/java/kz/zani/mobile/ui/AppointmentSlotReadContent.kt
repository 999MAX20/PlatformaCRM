package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.key
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.AppointmentSlotCandidateReview
import kz.zani.mobile.core.AppointmentSlotIntent

@Composable fun AppointmentSlotReadContent(model:AppointmentSlotReadViewModel,copy:Map<String,String>,language:String,isCurrent:()->Boolean,bookingBridge:((AppointmentSlotControl?,AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl?)?=null,useBookingCandidate:((AppointmentBookingCandidateControl)->Unit)?=null) {
    fun text(key:String)=copy[key] ?: key
    fun label(raw:String,id:Int)=(raw.ifEmpty {text("notAvailable")})+" · #$id"
    fun instant(raw:String,zone:String)=formatAppointmentDate(raw,zone,language) ?: raw
    val state=model.state;val control=model.presentation;val input=model.inputControl
    val readScope=text("appointments")+": "+text("slotReadTitle")
    if(!isCurrent() || !model.available || !model.matches(control))return
    if(!state.presented) {Button(onClick={if(isCurrent())model.open(control)}) {Text(text("slotReadOpen"))};return}
    Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text("slotReadTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        Text(text("slotReadBoundary"),style=MaterialTheme.typography.bodySmall)
        when {
            model.editing->{
                val invalidDay=state.day.isNotEmpty() && !AppointmentSlotIntent.validDay(state.day)
                key(input?.visit) {OutlinedTextField(value=state.day,onValueChange={if(isCurrent())model.setDayInput(it,input)},label={Text(text("slotReadDate"))},singleLine=true,isError=invalidDay,supportingText={if(invalidDay)Text(text("taskDraftAppointmentDayIssue"),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})})}
                Text(text("slotReadChooseResource"))
                Button(modifier=Modifier.semantics {selected=state.resourceMode==AppointmentSlotResourceMode.UNSPECIFIED},onClick={if(isCurrent())model.choose(AppointmentSlotResourceMode.UNSPECIFIED,control)}) {Text((if(state.resourceMode==AppointmentSlotResourceMode.UNSPECIFIED)"✓ " else "")+text("slotReadUnspecified"))}
                if(model.linkedResourceAvailable)Button(modifier=Modifier.semantics {selected=state.resourceMode==AppointmentSlotResourceMode.LINKED},onClick={if(isCurrent())model.choose(AppointmentSlotResourceMode.LINKED,control)}) {Text((if(state.resourceMode==AppointmentSlotResourceMode.LINKED)"✓ " else "")+text("slotReadLinkedResource"))}
                Button(enabled=model.canRead,onClick={if(isCurrent())model.submit(control)}) {Text(text("slotReadSubmit"))}
            }
            state.loading->CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            state.problem!=null->{
                Text(text(when(state.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(state.problem){kz.zani.mobile.core.ReadProblem.DENIED->"denied";kz.zani.mobile.core.ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"});liveRegion=LiveRegionMode.Polite})
                Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())model.retry(control)}) {Text(text("retry"))}
                Button(onClick={if(isCurrent())model.edit(control)}) {Text(text("slotReadEdit"))}
            }
            state.context!=null && state.read==state.context.read->{
                val context=state.context;val review=state.review;val candidate=review?.candidate
                if(review!=null && candidate!=null && review.validFor(context)) {
                    Text(text("slotReviewTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
                    Text(text("business")+": "+label(context.business.name,context.business.id))
                    Text(text("service")+": "+label(context.service.name,context.service.id))
                    Text(text("referenceResourceTitle")+": "+(context.resource?.let {label(it.name,it.id)} ?: text("slotReadUnspecified")))
                    Text(context.read.intent.day+" · "+context.read.intent.timezone,style=MaterialTheme.typography.labelSmall)
                    Text(text("intervalStart")+": "+instant(candidate.startAt,context.read.intent.timezone))
                    Text(text("intervalEnd")+": "+instant(candidate.endAt,context.read.intent.timezone))
                    Text(text("slotReviewBoundary"),style=MaterialTheme.typography.bodySmall)
                    val bridge=bookingBridge?.invoke(control,review)
                    if(bridge!=null && useBookingCandidate!=null)Button(onClick={if(isCurrent())useBookingCandidate(bridge)}) {Text(text("bookingUseCandidateTime"))}
                    Button(onClick={if(isCurrent())model.backToCandidates(control)}) {Text(text("slotReviewBack"))}
                } else {
                    Text(context.read.intent.day+" · "+context.read.intent.timezone,style=MaterialTheme.typography.labelSmall)
                    if(context.read.candidates.isEmpty())Text(text("slotReadEmpty"))
                    context.read.candidates.forEachIndexed {index,value->Column {
                        Text(text("intervalStart")+": "+instant(value.startAt,context.read.intent.timezone))
                        Text(text("intervalEnd")+": "+instant(value.endAt,context.read.intent.timezone))
                        Button(modifier=Modifier.semantics {contentDescription=text("slotReviewChoose")+": "+listOf(text("intervalStart")+": "+instant(value.startAt,context.read.intent.timezone),text("intervalEnd")+": "+instant(value.endAt,context.read.intent.timezone)).joinToString(", ")},onClick={if(isCurrent())model.selectCandidate(index,control)}) {Text(text("slotReviewChoose"))}
                    }}
                }
                Button(onClick={if(isCurrent())model.edit(control)}) {Text(text("slotReadEdit"))}
                Button(onClick={if(isCurrent())model.refresh(control)}) {Text(text("slotReviewRefresh"))}
            }
        }
        Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("back")},onClick={if(isCurrent())model.close(control)}) {Text(text("back"))}
    }
}
