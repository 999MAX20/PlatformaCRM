package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.NotificationMarkReadPhase

@Composable fun NotificationMarkReadContent(model:NotificationMarkReadModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val read=model.read ?: return
    val record=model.submission
    val review=model.review
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        if(model.blocked) {
            if(record!=null) {
                val key=when(record.phase) {NotificationMarkReadPhase.PENDING->"taskCommentFakePending";NotificationMarkReadPhase.CONFIRMED->"notificationFakeReadConfirmed";NotificationMarkReadPhase.REJECTED->"notificationFakeReadRejected";NotificationMarkReadPhase.UNKNOWN->"notificationFakeReadUnknown"}
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(record.phase==NotificationMarkReadPhase.CONFIRMED || record.phase==NotificationMarkReadPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("notificationFakeReadReview")+": "+text(if(record.phase==NotificationMarkReadPhase.CONFIRMED)"taskCommentFakeDone" else "notificationFakeReadEdit")},onClick={if(isCurrent())model.acknowledge(read,record.attempt.localID)}) {Text(text(if(record.phase==NotificationMarkReadPhase.CONFIRMED)"taskCommentFakeDone" else "notificationFakeReadEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if(review!=null && review.source==read) {
            Text(text("notificationFakeReadReview"),style=MaterialTheme.typography.labelLarge)
            Text(read.notification.text ?: text("notAvailable"))
            Button(onClick={if(isCurrent())model.launchSubmit(review,isCurrent)}) {Text(text("notificationFakeReadSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("notificationFakeReadReview")+": "+text("back")},onClick={if(isCurrent())model.back(review)}) {Text(text("back"))}
        } else if(model.canPrepare)TextButton(onClick={if(isCurrent())model.prepare(read)}) {Text(text("notificationFakeReadPrepare"))}
    }
}
