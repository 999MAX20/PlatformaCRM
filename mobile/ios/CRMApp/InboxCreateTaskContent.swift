import SwiftUI
import CRMCore

struct InboxCreateTaskContent:View {
    @ObservedObject var model:InboxCreateTaskViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxTaskCreateNone")}
    @ViewBuilder private func details(_ review:InboxCreateTaskReview)->some View {
        LabeledContent(AppCopy.text("inboxTaskCreateClient"),value:id(review.source.client));LabeledContent(AppCopy.text("inboxTaskCreateLead"),value:id(review.source.lead));LabeledContent(AppCopy.text("inboxTaskCreateActor"),value:id(review.authorization.actor));Text(AppCopy.text("inboxTaskCreateOmissions"))
    }
    var body:some View {
        let control=model.control
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxTaskCreateTitle")) {
                Text(AppCopy.text("inboxTaskCreateBoundary")).font(.caption)
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxTaskCreatePending":record.phase == .response ? "inboxTaskCreateResponse":record.phase == .rejected ? "inboxTaskCreateRejected":"inboxTaskCreateUnknown")).accessibilityAddTraits(.updatesFrequently)
                    details(record.attempt.review)
                    if let result=record.result {LabeledContent(AppCopy.text("inboxTaskCreateResultID"),value:id(result.id));Text(result.title)}
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxTaskCreateAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxTaskCreateTitle")+": "+AppCopy.text("inboxTaskCreateAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxTaskCreateRetained"))}
                else if let review=model.review {
                    details(review)
                    Button(AppCopy.text("inboxTaskCreateSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxTaskCreateTitle")+": "+AppCopy.text("back")))
                } else {
                    Text(AppCopy.text("inboxTaskCreateOmissions"))
                    Button(AppCopy.text("inboxTaskCreateReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
            }
        }
    }
}
