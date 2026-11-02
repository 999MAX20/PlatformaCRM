import SwiftUI
import CRMCore

struct AppointmentLifecycleContent:View {
    @ObservedObject var model:AppointmentLifecycleViewModel
    let isCurrent:@MainActor ()->Bool
    let prepare:@MainActor (AppointmentLifecycleAction,AppointmentLifecycleControl)->Void
    private func action(_ value:AppointmentLifecycleAction)->String {let key:String = switch value {case .confirm:"appointmentLifecycleConfirm";case .cancel:"appointmentLifecycleCancel";case .reschedule:"appointmentLifecycleReschedule";case .complete:"appointmentLifecycleComplete";case .noShow:"appointmentLifecycleNoShow"};return AppCopy.text(key)}
    private func phase(_ value:AppointmentLifecyclePhase)->String {switch value {case .pending:"taskCommentFakePending";case .acceptedFixture:"appointmentLifecycleAccepted";case .rejectedFixture:"appointmentLifecycleRejected";case .unknown:"appointmentLifecycleUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("appointmentLifecycle")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        Text(action(record.attempt.review.action))
                        Text(record.attempt.review.source.appointment.title ?? AppCopy.text("notAvailable"))
                        Text(AppCopy.text(phase(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let input=record.attempt.review.reschedule {AppointmentRescheduleSummary(input:input)}
                        if let receipt=record.terminalReceipt {LabeledContent(AppCopy.text("status"),value:AppointmentStatusText.label(receipt.status,text:AppCopy.text));Text(AppCopy.text("appointmentTerminalLimits"))}
                        if let receipt=record.receipt {
                            LabeledContent(AppCopy.text("status"),value:AppointmentStatusText.label(receipt.appointment.status,text:AppCopy.text))
                            if receipt.replayed {Text(AppCopy.text("appointmentLifecycleReplay"))}
                            if record.attempt.review.reschedule != nil {LabeledContent(AppCopy.text("intervalStart"),value:receipt.appointment.start_at);Text(AppCopy.text("appointmentRescheduleReceiptLimits"))}
                        }
                        if record.phase == .acceptedFixture || record.phase == .rejectedFixture {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("appointmentLifecycle")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if let review=model.review {
                    Text(AppCopy.text("appointmentLifecycleReview"))
                    Text(action(review.action))
                    Text(review.source.appointment.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("business"),value:review.source.read.scope.business.name)
                    if let input=review.reschedule {AppointmentRescheduleSummary(input:input);Text(AppCopy.text("appointmentRescheduleReceiptLimits"))}
                    if review.action.isGenericTerminal {Text(AppCopy.text("appointmentTerminalLimits"))}
                    Button(AppCopy.text("appointmentLifecycleSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("appointmentLifecycle")+": "+AppCopy.text("back")))
                } else if model.reschedulePresented {AppointmentRescheduleFields(model:model,isCurrent:isCurrent)} else {
                    ForEach(AppointmentLifecycleAction.allCases,id:\.self) {value in
                        if model.canPrepare(value) {Button(action(value)) {if isCurrent() {prepare(value,control)}}}
                    }
                }
            }
        }
    }
}

private struct AppointmentRescheduleSummary:View {
    let input:AppointmentRescheduleInput
    private var resource:String {switch input.resource {case .clear:AppCopy.text("appointmentRescheduleClear");case .linked(let value):value.name}}
    var body:some View {
        LabeledContent(AppCopy.text("appointmentRescheduleTime"),value:input.start.raw)
        LabeledContent(AppCopy.text("resource"),value:resource)
        if !input.reason.isEmpty {LabeledContent(AppCopy.text("appointmentRescheduleReason"),value:input.reason)}
    }
}
private struct AppointmentRescheduleFields:View {
    @ObservedObject var model:AppointmentLifecycleViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        if let control=model.control {
            let input=model.inputControl
            Text(AppCopy.text("appointmentRescheduleTimeHint"))
            TextField(AppCopy.text("appointmentRescheduleTime"),text:Binding(get:{model.rawStart},set:{if isCurrent() {model.setStart($0,expected:input)}})).id("start/\(input?.visit ?? -1)").disabled(!model.editingReschedule).accessibilityHint(!model.rawStart.isEmpty && !model.timeInputValid ? AppCopy.text("appointmentRescheduleTimeInvalid") : "")
            if !model.rawStart.isEmpty && !model.timeInputValid {Text(AppCopy.text("appointmentRescheduleTimeInvalid")).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
            TextField(AppCopy.text("appointmentRescheduleReason"),text:Binding(get:{model.rawReason},set:{if isCurrent() {model.setReason($0,expected:input)}}),axis:.vertical).id("reason/\(input?.visit ?? -1)").disabled(!model.editingReschedule)
            if model.resourceLoading {ProgressView(AppCopy.text("loading"))}
            if let failure=model.resourceFailure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently)}
            if let selected=model.resourceChoice {switch selected {case .clear:Text(AppCopy.text("appointmentRescheduleClear"));case .linked(let value):Text(value.name)}}
            else {Text(AppCopy.text("appointmentRescheduleChoice"))}
            Button(AppCopy.text("appointmentRescheduleClear")) {if isCurrent() {model.chooseClear(expected:control)}}.disabled(!model.editingReschedule)
            if model.linkedResourceAvailable {Button(AppCopy.text("appointmentRescheduleLinked")) {Task {if isCurrent() {await model.loadLinkedResource(expected:control)}}}.disabled(!model.editingReschedule)}
            Button(AppCopy.text("appointmentRescheduleReview")) {if isCurrent() {model.reviewReschedule(expected:control)}}.disabled(!model.canReviewReschedule)
            Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("appointmentLifecycle")+": "+AppCopy.text("back")))
        }
    }
}
