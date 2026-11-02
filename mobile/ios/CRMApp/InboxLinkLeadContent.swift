import SwiftUI
import CRMCore

struct InboxLinkLeadContent:View {
    @ObservedObject var model:InboxLinkLeadViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxLeadNone")}
    @ViewBuilder private func original(_ source:InboxLinkLeadSource)->some View {LabeledContent(AppCopy.text("inboxLeadOriginal"),value:id(source.lead));LabeledContent(AppCopy.text("inboxLeadOriginalClient"),value:id(source.client))}
    @ViewBuilder private func candidate(_ review:InboxLinkLeadReview)->some View {
        Text(review.candidate.reference.detail.lead.title+" · #\(review.candidate.reference.detail.lead.id)");Text(review.candidate.reference.rawQuery)
        LabeledContent(AppCopy.text("inboxLeadExpectedClient"),value:id(review.source.client ?? review.candidate.reference.detail.lead.client_id))
    }
    var body:some View {
        let control=model.control
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxLeadTitle")) {
                Text(AppCopy.text("inboxLeadBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading"))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxLeadPending":record.phase == .response ? "inboxLeadResponse":record.phase == .rejected ? "inboxLeadRejected":"inboxLeadUnknown")).accessibilityAddTraits(.updatesFrequently)
                    original(record.attempt.review.source);candidate(record.attempt.review)
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxLeadAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLeadTitle")+": "+AppCopy.text("inboxLeadAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxLeadRetained"))}
                else if let review=model.review {
                    original(review.source);candidate(review)
                    Button(AppCopy.text("inboxLeadSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLeadTitle")+": "+AppCopy.text("back")))
                } else {
                    if let source=model.source {original(source)}
                    Button(AppCopy.text("inboxLeadReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxLeadLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}}
            }
        }
    }
}
