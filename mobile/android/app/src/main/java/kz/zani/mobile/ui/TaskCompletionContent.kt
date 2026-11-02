package kz.zani.mobile.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskCompletionContent(model:TaskCompletionModel,copy:Map<String,String>,isCurrent:()->Boolean,prepare:(TaskCompletionControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskCompleteAction"),style=MaterialTheme.typography.titleSmall)
            Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.source.task.title ?: text("notAvailable"))
                        val key=when(record.phase) {TaskCompletionPhase.PENDING->"taskCommentFakePending";TaskCompletionPhase.CONFIRMED->"taskCompleteFakeConfirmed";TaskCompletionPhase.REJECTED->"taskCompleteFakeRejected";TaskCompletionPhase.UNKNOWN->"taskCompleteFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        if(record.phase==TaskCompletionPhase.CONFIRMED || record.phase==TaskCompletionPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskCompleteAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskCompleteFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("status")+": "+text("taskDone"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskCompleteFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskCompleteAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.canPrepare->TextButton(onClick={if(isCurrent())prepare(control)}) {Text(text("taskCompleteAction"))}
            }
        }
    }
}
