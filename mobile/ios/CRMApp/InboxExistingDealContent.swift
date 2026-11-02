import SwiftUI
import CRMCore

struct InboxExistingDealContent:View {
    @ObservedObject var model:InboxExistingDealViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxExistingDealNone")}
    @ViewBuilder private func source(_ source:InboxExistingDealSource)->some View {if let deal=source.deal {LabeledContent(AppCopy.text("inboxExistingDealOriginal"),value:"#\(deal)")} else {Text(AppCopy.text("inboxExistingDealAbsent"))};LabeledContent(AppCopy.text("inboxExistingDealConversationClient"),value:id(source.client));LabeledContent(AppCopy.text("inboxExistingDealConversationLead"),value:id(source.lead))}
    var body:some View {
        let control=model.control;let readScope=AppCopy.text("inboxExistingDealTitle")
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxExistingDealTitle")) {
                Text(AppCopy.text("inboxExistingDealBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(error)))}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxExistingDealPending":record.phase == .response ? "inboxExistingDealResponse":record.phase == .rejected ? "inboxExistingDealRejected":"inboxExistingDealUnknown")).accessibilityAddTraits(.updatesFrequently)
                    source(record.attempt.review.source)
                    if let result=record.result {LabeledContent(AppCopy.text("inboxExistingDealResultID"),value:"#\(result.id)");LabeledContent(AppCopy.text("inboxExistingDealResultClient"),value:id(result.client));LabeledContent(AppCopy.text("inboxExistingDealResultLead"),value:id(result.lead));Text(result.title)}
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxExistingDealAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxExistingDealTitle")+": "+AppCopy.text("inboxExistingDealAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxExistingDealRetained"))}
                else if let review=model.review {
                    source(review.source);Text(AppCopy.text("inboxExistingDealOmissions"))
                    Button(AppCopy.text("inboxExistingDealSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    if let observed=model.source {source(observed)}
                    Button(AppCopy.text("inboxExistingDealReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxExistingDealLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("inboxExistingDealLoad")))}
            }
        }
    }
}
