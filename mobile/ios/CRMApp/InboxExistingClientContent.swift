import SwiftUI
import CRMCore

struct InboxExistingClientContent:View {
    @ObservedObject var model:InboxExistingClientViewModel
    let isCurrent:@MainActor ()->Bool
    @ViewBuilder private func source(_ source:InboxExistingClientSource)->some View {if let id=source.client {LabeledContent(AppCopy.text("inboxExistingOriginal"),value:"#\(id)")} else {Text(AppCopy.text("inboxExistingAbsent"))}}
    var body:some View {
        let control=model.control;let readScope=AppCopy.text("inboxExistingTitle")
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxExistingTitle")) {
                Text(AppCopy.text("inboxExistingBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(error)))}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxExistingPending":record.phase == .response ? "inboxExistingResponse":record.phase == .rejected ? "inboxExistingRejected":"inboxExistingUnknown")).accessibilityAddTraits(.updatesFrequently)
                    source(record.attempt.review.source)
                    if let result=record.result {LabeledContent(AppCopy.text("inboxExistingResultID"),value:"#\(result.id)");Text(result.fullName);Text(result.phone);Text(result.email)}
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxExistingAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxExistingTitle")+": "+AppCopy.text("inboxExistingAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxExistingRetained"))}
                else if let review=model.review {
                    source(review.source);Text(AppCopy.text("inboxExistingOmissions"))
                    Button(AppCopy.text("inboxExistingSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    if let observed=model.source {source(observed)}
                    Button(AppCopy.text("inboxExistingReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxExistingLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("inboxExistingLoad")))}
            }
        }
    }
}
