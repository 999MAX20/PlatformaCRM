import SwiftUI
import CRMCore

struct InboxTargetAssignmentContent:View {
    @ObservedObject var model:InboxTargetAssignmentViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxTargetNone")}
    @ViewBuilder private func original(_ source:InboxTargetAssignmentSource)->some View {LabeledContent(AppCopy.text("inboxTargetOriginal"),value:id(source.assignedTo))}
    @ViewBuilder private func candidate(_ review:InboxTargetAssignmentReview)->some View {
        let ref=review.candidate.reference
        Text(ref.source.user.displayName ?? AppCopy.text("notAvailable"));Text(ref.source.user.email)
        LabeledContent(AppCopy.text("inboxTargetUser"),value:id(ref.source.user.id))
        LabeledContent(AppCopy.text("inboxTargetMembership"),value:id(ref.source.id))
        Text(ref.rawInput)
    }
    var body:some View {
        let control=model.control;let readScope=AppCopy.text("inboxTargetTitle")
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxTargetTitle")) {
                Text(AppCopy.text("inboxTargetBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                if let error=model.failure {Text(AppCopy.error(error)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(error)))}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxTargetPending":record.phase == .response ? "inboxTargetResponse":record.phase == .rejected ? "inboxTargetRejected":"inboxTargetUnknown")).accessibilityAddTraits(.updatesFrequently)
                    original(record.attempt.review.source);candidate(record.attempt.review)
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxTargetAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxTargetTitle")+": "+AppCopy.text("inboxTargetAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxTargetRetained"))}
                else if let review=model.review {
                    original(review.source);candidate(review)
                    Button(AppCopy.text("inboxTargetSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    if let source=model.source {original(source)}
                    Button(AppCopy.text("inboxTargetReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                }
                if model.canLoad {Button(AppCopy.text("inboxTargetLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("inboxTargetLoad")))}
            }
        }
    }
}
