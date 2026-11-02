package kz.zani.mobile.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskStartContent(model:TaskStartModel,copy:Map<String,String>,isCurrent:()->Boolean,prepare:(TaskStartControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    fun person(value:MobileUserRead)=when(value) {MobileUserRead.NotSet->text("taskNoAssignee");MobileUserRead.Unknown->text("notAvailable");is MobileUserRead.Person->value.user.displayName ?: text("notAvailable")}
    val control=model.control
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskStartAction"),style=MaterialTheme.typography.titleSmall)
            Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.source.task.title ?: text("notAvailable"))
                        val key=when(record.phase) {TaskStartPhase.PENDING->"taskCommentFakePending";TaskStartPhase.CONFIRMED->"taskStartFakeConfirmed";TaskStartPhase.REJECTED->"taskStartFakeRejected";TaskStartPhase.UNKNOWN->"taskStartFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        if(record.phase==TaskStartPhase.CONFIRMED || record.phase==TaskStartPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskStartAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskStartFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("status")+": "+text("taskInProgress"));Text(text("taskAssignee")+": "+person(review.source.assignee));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskStartFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskStartAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.canPrepare->TextButton(onClick={if(isCurrent())prepare(control)}) {Text(text("taskStartAction"))}
            }
        }
    }
}
