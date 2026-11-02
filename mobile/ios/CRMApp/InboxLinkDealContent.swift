import SwiftUI
import CRMCore

struct InboxLinkDealContent:View {
    @ObservedObject var model:InboxLinkDealViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxDealNone")}
    @ViewBuilder private func original(_ source:InboxLinkDealSource)->some View {LabeledContent(AppCopy.text("inboxDealOriginal"),value:id(source.deal));LabeledContent(AppCopy.text("inboxDealOriginalClient"),value:id(source.client));LabeledContent(AppCopy.text("inboxDealOriginalLead"),value:id(source.lead))}
    @ViewBuilder private func candidate(_ review:InboxLinkDealReview)->some View {
        Text(review.candidate.reference.source.title+" · #\(review.candidate.reference.source.id)");Text(review.candidate.reference.rawInput)
        LabeledContent(AppCopy.text("inboxDealExpectedClient"),value:id(review.source.client ?? review.candidate.reference.source.client))
        LabeledContent(AppCopy.text("inboxDealExpectedLead"),value:id(review.source.lead ?? review.candidate.reference.source.lead))
    }
    var body:some View {
        let control=model.control
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxDealTitle")) {
                Text(AppCopy.text("inboxDealBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading"))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently)}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxDealPending":record.phase == .response ? "inboxDealResponse":record.phase == .rejected ? "inboxDealRejected":"inboxDealUnknown")).accessibilityAddTraits(.updatesFrequently)
                    original(record.attempt.review.source);candidate(record.attempt.review)
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxDealAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxDealTitle")+": "+AppCopy.text("inboxDealAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxDealRetained"))}
                else if let review=model.review {
                    original(review.source);candidate(review)
                    Button(AppCopy.text("inboxDealSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxDealTitle")+": "+AppCopy.text("back")))
                } else {
                    if let source=model.source {original(source)}
                    Button(AppCopy.text("inboxDealReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxDealLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}}
            }
        }
    }
}
