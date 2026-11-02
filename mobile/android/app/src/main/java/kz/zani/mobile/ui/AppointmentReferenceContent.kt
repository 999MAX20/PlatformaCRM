package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun AppointmentReferenceContent(links:AppointmentRelationsViewModel,kind:AppointmentReferenceKind,copy:Map<String,String>,modifier:Modifier=Modifier,language:String="en",isCurrent:()->Boolean,bookingBridge:((AppointmentSlotControl?,AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl?)?=null,useBookingCandidate:((AppointmentBookingCandidateControl)->Unit)?=null) {
    fun text(key:String)=copy[key] ?: key
    val state=links.state;val presentation=links.presentation
    if(!isCurrent() || !links.matches(presentation))return
    val readScope=text("appointments")+": "+text(if(kind==AppointmentReferenceKind.SERVICE)"service" else "referenceResourceTitle")+": "+text("details")
    Column(modifier.verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        Text(text(if(kind==AppointmentReferenceKind.SERVICE)"service" else "referenceResourceTitle"),style=MaterialTheme.typography.titleMedium,modifier=Modifier.semantics {heading()})
        when {
            state.loading->CircularProgressIndicator(Modifier.semantics {contentDescription=readScope+": "+text("loading");liveRegion=LiveRegionMode.Polite})
            state.problem!=null->{Text(text(when(state.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"}),modifier=Modifier.semantics {contentDescription=readScope+": "+text(when(state.problem){ReadProblem.DENIED->"denied";ReadProblem.NOT_FOUND->"notAvailable";else->"unavailable"});liveRegion=LiveRegionMode.Polite});Button(modifier=Modifier.semantics {contentDescription=readScope+": "+text("retry")},onClick={if(isCurrent())links.retry(presentation)}) {Text(text("retry"))}}
            state.reference!=null->{val detail=state.reference;Text(detail.name.ifEmpty {text("notAvailable")},style=MaterialTheme.typography.titleSmall);Text(text("referenceActivityTitle")+": "+text(detail.activityCopyKey));if(kind==AppointmentReferenceKind.RESOURCE)Text(text(detail.resourceTypeCopyKey));Text(text("referenceReadOnly"),style=MaterialTheme.typography.bodySmall);Text(text("referenceNoBookingProof"),style=MaterialTheme.typography.bodySmall);if(kind==AppointmentReferenceKind.SERVICE)AppointmentSlotReadContent(links.slotReads,copy,language,isCurrent={isCurrent() && links.matches(presentation)},bookingBridge=bookingBridge,useBookingCandidate=useBookingCandidate)}
        }
    }
}
