package kz.zani.mobile.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun TaskUndoCancelContent(model:TaskUndoCancelModel,copy:Map<String,String>,isCurrent:()->Boolean,prepare:(TaskUndoCancelControl)->Unit) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control
    if(isCurrent() && model.canPresent && control!=null) {
        Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(text("taskUndoCancelAction"),style=MaterialTheme.typography.titleSmall)
            Text(text("fixtureMode"),style=MaterialTheme.typography.labelSmall)
            when {
                model.blocked->{val record=model.submission
                    if(record==null)Text(text("taskCommentFakeQuarantined")) else {
                        Text(record.attempt.review.source.task.title ?: text("notAvailable"))
                        val key=when(record.phase) {TaskUndoCancelPhase.PENDING->"taskCommentFakePending";TaskUndoCancelPhase.CONFIRMED->"taskUndoCancelFakeConfirmed";TaskUndoCancelPhase.REJECTED->"taskUndoCancelFakeRejected";TaskUndoCancelPhase.UNKNOWN->"taskUndoCancelFakeUnknown"}
                        Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                        if(record.phase==TaskUndoCancelPhase.CONFIRMED)record.result?.let {result->Text(text("status")+": "+text(when(result.status) {"done"->"taskDone";"in_progress"->"taskInProgress";else->"taskOpen"}));result.completedAt?.let {Text(text("taskUndoCancelCompletionAt")+": "+it)}}
                        if(record.phase==TaskUndoCancelPhase.CONFIRMED || record.phase==TaskUndoCancelPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("taskUndoCancelAction")+": "+text("taskCommentFakeDone")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text("taskCommentFakeDone"))}
                    }
                }
                model.consumed->Text(text("taskUndoCancelFakeConfirmed"))
                model.review!=null->{val review=model.review!!;Text(review.source.task.title ?: text("notAvailable"));Text(text("taskUndoCancelContract"));Button(onClick={if(isCurrent())model.launchSubmit(control)}) {Text(text("taskUndoCancelFakeSubmit"))};TextButton(modifier=Modifier.semantics {contentDescription=text("taskUndoCancelAction")+": "+text("back")},onClick={if(isCurrent())model.back(control)}) {Text(text("back"))}}
                model.canPrepare->TextButton(onClick={if(isCurrent())prepare(control)}) {Text(text("taskUndoCancelAction"))}
            }
        }
    }
}
