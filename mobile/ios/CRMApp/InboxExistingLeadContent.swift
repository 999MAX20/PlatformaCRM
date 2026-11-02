import SwiftUI
import CRMCore

struct InboxExistingLeadContent:View {
    @ObservedObject var model:InboxExistingLeadViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxExistingLeadNone")}
    @ViewBuilder private func source(_ source:InboxExistingLeadSource)->some View {if let lead=source.lead {LabeledContent(AppCopy.text("inboxExistingLeadOriginal"),value:"#\(lead)")} else {Text(AppCopy.text("inboxExistingLeadAbsent"))};LabeledContent(AppCopy.text("inboxExistingLeadConversationClient"),value:id(source.client))}
    var body:some View {
        let control=model.control;let readScope=AppCopy.text("inboxExistingLeadTitle")
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxExistingLeadTitle")) {
                Text(AppCopy.text("inboxExistingLeadBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(error)))}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxExistingLeadPending":record.phase == .response ? "inboxExistingLeadResponse":record.phase == .rejected ? "inboxExistingLeadRejected":"inboxExistingLeadUnknown")).accessibilityAddTraits(.updatesFrequently)
                    source(record.attempt.review.source)
                    if let result=record.result {LabeledContent(AppCopy.text("inboxExistingLeadResultID"),value:"#\(result.id)");LabeledContent(AppCopy.text("inboxExistingLeadResultClient"),value:id(result.client));Text(result.message)}
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxExistingLeadAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxExistingLeadTitle")+": "+AppCopy.text("inboxExistingLeadAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxExistingLeadRetained"))}
                else if let review=model.review {
                    source(review.source);Text(AppCopy.text("inboxExistingLeadOmissions"))
                    Button(AppCopy.text("inboxExistingLeadSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    if let observed=model.source {source(observed)}
                    Button(AppCopy.text("inboxExistingLeadReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxExistingLeadLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("inboxExistingLeadLoad")))}
            }
        }
    }
}
