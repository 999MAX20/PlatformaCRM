package kz.zani.mobile.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.*
import androidx.compose.ui.unit.dp
import kz.zani.mobile.core.*

@Composable fun InboxReplyReceiptContent(model:ReplyDraftModel,copy:Map<String,String>,isCurrent:()->Boolean) {
    fun text(key:String)=copy[key] ?: key
    val control=model.control;val record=model.submission
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
        Text(text("inboxReplyReceipt"),style=MaterialTheme.typography.titleSmall)
        if(record==null)Text(text("taskCommentFakeQuarantined")) else {
            Text(record.attempt.review.text)
            val key=when(record.phase){InboxReplyPhase.PENDING->"taskCommentFakePending";InboxReplyPhase.CONFIRMED->"inboxReplyFakeConfirmed";InboxReplyPhase.REJECTED->"inboxReplyFakeRejected";InboxReplyPhase.UNKNOWN->"inboxReplyFakeUnknown"}
            Text(text(key),modifier=Modifier.semantics {liveRegion=LiveRegionMode.Polite})
            record.receipt?.let {receipt->Text(text(when(receipt.delivery){InboxReplyDelivery.QUEUED->"inboxReplyReceiptQueued";InboxReplyDelivery.SENT->"inboxReplyReceiptSent";InboxReplyDelivery.FAILED->"inboxReplyReceiptFailed"}));Text(text(if(receipt.replayed)"inboxReplyReceiptReplayed" else "inboxReplyReceiptNew"));Text(text("inboxReplyNoDeliveryProof"),style=MaterialTheme.typography.bodySmall)}
            if(record.phase==InboxReplyPhase.CONFIRMED || record.phase==InboxReplyPhase.REJECTED)TextButton(modifier=Modifier.semantics {contentDescription=text("replyDraftTitle")+": "+text(if(record.phase==InboxReplyPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit")},onClick={if(isCurrent())model.acknowledge(control,record)}) {Text(text(if(record.phase==InboxReplyPhase.CONFIRMED)"taskCommentFakeDone" else "taskCommentFakeEdit"))}
        }
    }
}
