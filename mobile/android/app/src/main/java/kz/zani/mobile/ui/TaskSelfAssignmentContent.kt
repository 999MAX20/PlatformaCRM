package kz.zani.mobile.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskSelfAssignmentContent(model:TaskSelfAssignmentModel,copy:Map<String,String>,isCurrent:()->Boolean,prepare:(TaskSelfAssignmentControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskSelfAssignAction"),style=MaterialTheme.typography.titleSmall)
            Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.source.task.title ?: text("notAvailable"))
                        val key=when(record.phase) {TaskSelfAssignmentPhase.PENDING->"taskCommentFakePending";TaskSelfAssignmentPhase.CONFIRMED->"taskSelfAssignFakeConfirmed";TaskSelfAssignmentPhase.REJECTED->"taskSelfAssignFakeRejected";TaskSelfAssignmentPhase.UNKNOWN->"taskSelfAssignFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        if(record.phase==TaskSelfAssignmentPhase.CONFIRMED || record.phase==TaskSelfAssignmentPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskSelfAssignAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskSelfAssignFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("status")+": "+text("taskInProgress"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskSelfAssignFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskSelfAssignAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.canPrepare->TextButton(onClick={if(isCurrent())prepare(control)}) {Text(text("taskSelfAssignAction"))}
            }
        }
    }
}
