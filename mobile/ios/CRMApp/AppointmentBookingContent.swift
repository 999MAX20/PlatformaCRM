import SwiftUI
import CRMCore

struct AppointmentBookingSection:View {
    @ObservedObject var agenda:AgendaViewModel
    @ObservedObject var model:AppointmentBookingViewModel
    var body:some View {if let peer=agenda.lifecycle {AppointmentBookingPeerSection(agenda:agenda,model:model,peer:peer)} else {AppointmentBookingOwnedSection(agenda:agenda,model:model)}}
}
private struct AppointmentBookingPeerSection:View {
    @ObservedObject var agenda:AgendaViewModel
    @ObservedObject var model:AppointmentBookingViewModel
    @ObservedObject var peer:AppointmentLifecycleViewModel
    var body:some View {AppointmentBookingOwnedSection(agenda:agenda,model:model)}
}
private struct AppointmentBookingOwnedSection:View {
    @ObservedObject var agenda:AgendaViewModel
    @ObservedObject var model:AppointmentBookingViewModel
    var body:some View {
        if let entry=agenda.bookingEntryControl {
            AppointmentBookingContent(model:model,isCurrent:{agenda.matchesBookingEntry(entry)},open:{agenda.openBooking(entry:entry,child:$0)},back:{agenda.backBooking(entry:entry,child:$0)},acknowledge:{agenda.acknowledgeBooking(entry:entry,child:$0,record:$1)})
        }
    }
}
private struct AppointmentBookingContent:View {
    @ObservedObject var model:AppointmentBookingViewModel
    let isCurrent:@MainActor ()->Bool
    let open:@MainActor (AppointmentBookingControl?)->Void
    let back:@MainActor (AppointmentBookingControl?)->Void
    let acknowledge:@MainActor (AppointmentBookingControl?,AppointmentBookingRecord)->Void
    private func phase(_ value:AppointmentBookingPhase)->String {switch value {case .pending:"taskCommentFakePending";case .acceptedFixture:"appointmentLifecycleAccepted";case .rejectedFixture:"appointmentLifecycleRejected";case .unknown:"appointmentLifecycleUnknown"}}
    var body:some View {
        if isCurrent(),model.canPresent,let control=model.control {
            Section(AppCopy.text("bookingTitle")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                if model.blocked {
                    if let record=model.submission {
                        AppointmentBookingSummary(source:record.attempt.review.source,input:record.attempt.review.input)
                        Text(AppCopy.text(phase(record.phase))).accessibilityAddTraits(.updatesFrequently)
                        if let receipt=record.receipt {
                            Text("#\(receipt.appointment.id)")
                            LabeledContent(AppCopy.text("status"),value:AppointmentStatusText.label(receipt.appointment.status,text:AppCopy.text))
                            Text(AppCopy.text("bookingLimits"))
                        }
                        if record.phase == .acceptedFixture || record.phase == .rejectedFixture {Button(AppCopy.text("taskCommentFakeDone")) {if isCurrent() {acknowledge(control,record)}}.accessibilityLabel(Text(AppCopy.text("bookingTitle")+": "+AppCopy.text("taskCommentFakeDone")))}
                    } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                } else if let review=model.review {
                    AppointmentBookingSummary(source:review.source,input:review.input)
                    Text(AppCopy.text("bookingLimits"))
                    Button(AppCopy.text("appointmentLifecycleSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}
                    Button(AppCopy.text("back")) {if isCurrent() {back(control)}}.accessibilityLabel(Text(AppCopy.text("bookingTitle")+": "+AppCopy.text("back")))
                } else if model.presented {
                    AppointmentBookingDirectoryAccess(model:model,isCurrent:isCurrent)
                    let input=model.inputControl
                    Text(AppCopy.text("appointmentRescheduleTimeHint"))
                    TextField(AppCopy.text("appointmentRescheduleTime"),text:Binding(get:{model.rawStart},set:{if isCurrent() {model.setStart($0,expected:input)}})).id(input?.visit).disabled(!model.editing).accessibilityHint(!model.rawStart.isEmpty && !model.timeValid ? AppCopy.text("appointmentRescheduleTimeInvalid") : "")
                    if !model.rawStart.isEmpty && !model.timeValid {Text(AppCopy.text("appointmentRescheduleTimeInvalid")).accessibilityAddTraits(.updatesFrequently).accessibilityHidden(true)}
                    LabeledContent(AppCopy.text("client"),value:model.client?.title ?? AppCopy.text("notAvailable"))
                    Button(AppCopy.text("bookingReadClient")) {Task {if isCurrent() {await model.load(.client,expected:control)}}}.disabled(!model.editing)
                    LabeledContent(AppCopy.text("service"),value:model.service?.name ?? AppCopy.text("notAvailable"))
                    Button(AppCopy.text("bookingReadService")) {Task {if isCurrent() {await model.load(.service,expected:control)}}}.disabled(!model.editing)
                    Text(model.resource.map {value in switch value {case .clear:AppCopy.text("appointmentRescheduleClear");case .linked(let detail):detail.name}} ?? AppCopy.text("appointmentRescheduleChoice"))
                    Button(AppCopy.text("appointmentRescheduleClear")) {if isCurrent() {model.chooseClear(expected:control)}}.disabled(!model.editing)
                    if model.linkedResourceAvailable {Button(AppCopy.text("bookingReadResource")) {Task {if isCurrent() {await model.load(.resource,expected:control)}}}.disabled(!model.editing)}
                    if model.loading != nil {ProgressView(AppCopy.text("loading"))}
                    if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("bookingReview")) {if isCurrent() {model.prepareReview(expected:control)}}.disabled(!model.canReview)
                    Button(AppCopy.text("back")) {if isCurrent() {back(control)}}.accessibilityLabel(Text(AppCopy.text("bookingTitle")+": "+AppCopy.text("back")))
                } else {Button(AppCopy.text("bookingOpen")) {if isCurrent() {open(control)}}.disabled(!model.canOpen)}
            }
        }
    }
}
private struct AppointmentBookingSummary:View {
    let source:AppointmentBookingSource;let input:AppointmentBookingInput
    private var resource:String {switch input.resource {case .clear:AppCopy.text("appointmentRescheduleClear");case .linked(let detail):detail.name+" · #\(detail.id)"}}
    var body:some View {
        LabeledContent(AppCopy.text("business"),value:source.read.scope.business.name)
        LabeledContent(AppCopy.text("client"),value:(input.client.title ?? AppCopy.text("notAvailable"))+" · #\(input.client.id)")
        LabeledContent(AppCopy.text("service"),value:input.service.name+" · #\(input.service.id)")
        LabeledContent(AppCopy.text("resource"),value:resource)
        LabeledContent(AppCopy.text("intervalStart"),value:input.start.raw)
    }
}
