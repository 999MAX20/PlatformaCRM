package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.NotificationMarkUnreadPhase

@Composable fun NotificationMarkUnreadContent(model:NotificationMarkUnreadModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val read=model.read ?: return
    val record=model.submission
    val review=model.review
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        if(model.blocked) {
            if(record!=null) {
                val key=when(record.phase) {NotificationMarkUnreadPhase.PENDING->"taskCommentFakePending";NotificationMarkUnreadPhase.CONFIRMED->"notificationFakeUnreadConfirmed";NotificationMarkUnreadPhase.REJECTED->"notificationFakeUnreadRejected";NotificationMarkUnreadPhase.UNKNOWN->"notificationFakeUnreadUnknown"}
                Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
                if(record.phase==NotificationMarkUnreadPhase.CONFIRMED || record.phase==NotificationMarkUnreadPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("notificationFakeUnreadReview")+": "+text(if(record.phase==NotificationMarkUnreadPhase.CONFIRMED)"taskCommentFakeDone" else "notificationFakeUnreadEdit")},onClick={if(isCurrent())model.acknowledge(read,record.attempt.localID)}) {Text(text(if(record.phase==NotificationMarkUnreadPhase.CONFIRMED)"taskCommentFakeDone" else "notificationFakeUnreadEdit"))}
            } else Text(text("taskCommentFakeQuarantined"))
        } else if(review!=null && review.source==read) {
            Text(text("notificationFakeUnreadReview"),style=MaterialTheme.typography.labelLarge)
            Text(read.notification.text ?: text("notAvailable"))
            Button(onClick={if(isCurrent())model.launchSubmit(review,isCurrent)}) {Text(text("notificationFakeUnreadSubmit"))}
            TextButton(modifier=Modifier.semantics {contentDescription=text("notificationFakeUnreadReview")+": "+text("back")},onClick={if(isCurrent())model.back(review)}) {Text(text("back"))}
        } else if(model.canPrepare)TextButton(onClick={if(isCurrent())model.prepare(read)}) {Text(text("notificationFakeUnreadPrepare"))}
    }
}
