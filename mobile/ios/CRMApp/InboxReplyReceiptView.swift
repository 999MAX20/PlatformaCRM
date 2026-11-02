import SwiftUI
import CRMCore

struct InboxReplyReceiptView:View {
    @ObservedObject var model:ReplyDraftViewModel
    let isCurrent:@MainActor ()->Bool
    private func phase(_ value:InboxReplyPhase)->String {switch value {case .pending:"taskCommentFakePending";case .confirmed:"inboxReplyFakeConfirmed";case .rejected:"inboxReplyFakeRejected";case .unknown:"inboxReplyFakeUnknown"}}
    private func delivery(_ value:InboxReplyDelivery)->String {switch value {case .queued:"inboxReplyReceiptQueued";case .sent:"inboxReplyReceiptSent";case .failed:"inboxReplyReceiptFailed"}}
    var body:some View {
        let control=model.control
        Section(AppCopy.text("inboxReplyReceipt")) {
            if let record=model.submission {
                Text(record.attempt.review.text).textSelection(.enabled)
                Text(AppCopy.text(phase(record.phase))).accessibilityAddTraits(.updatesFrequently)
                if let receipt=record.receipt {
                    Text(AppCopy.text(delivery(receipt.delivery)))
                    Text(AppCopy.text(receipt.replayed ? "inboxReplyReceiptReplayed":"inboxReplyReceiptNew"))
                    Text(AppCopy.text("inboxReplyNoDeliveryProof")).font(.caption)
                }
                if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("replyDraftTitle")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")))}
            } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
        }
    }
}
