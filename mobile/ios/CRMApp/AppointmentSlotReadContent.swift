import SwiftUI
import CRMCore

struct AppointmentSlotReadContent:View {
    @ObservedObject var model:AppointmentSlotReadViewModel
    let isCurrent:@MainActor ()->Bool
    var bookingBridge:(@MainActor (AppointmentSlotControl?,AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl?)? = nil
    var useBookingCandidate:(@MainActor (AppointmentBookingCandidateControl)->Void)? = nil
    private func label(_ raw:String,id:Int)->String {(raw.isEmpty ? AppCopy.text("notAvailable"):raw)+" · #\(id)"}
    private func instant(_ value:String,zone:String)->String {AppointmentDate.format(startAt:value,timezone:zone,language:AppCopy.language) ?? value}
    var body:some View {
        let control=model.presentation,input=model.inputControl
        let readScope=AppCopy.text("appointments")+": "+AppCopy.text("slotReadTitle")
        Group {
            if isCurrent(),model.available,model.matches(control) {
                if !model.presented {
                    Button(AppCopy.text("slotReadOpen")) {if isCurrent() {model.open(control)}}
                } else {
                    VStack(alignment:.leading,spacing:12) {
                        Text(AppCopy.text("slotReadTitle")).font(.headline)
                        Text(AppCopy.text("slotReadBoundary")).font(.caption)
                        if model.editing {
                            let invalidDay = !model.day.isEmpty && !AppointmentSlotIntent.validDay(model.day)
                            TextField(AppCopy.text("slotReadDate"),text:Binding(get:{model.day},set:{if isCurrent() {model.setDayInput($0,input:input)}})).id(input?.visit).accessibilityHint(invalidDay ? AppCopy.text("taskDraftAppointmentDayIssue") : "")
                            if invalidDay {Text(AppCopy.text("taskDraftAppointmentDayIssue")).foregroundStyle(.red).accessibilityHidden(true)}
                            Text(AppCopy.text("slotReadChooseResource")).font(.subheadline)
                            Button((model.resourceMode == .unspecified ? "✓ ":"")+AppCopy.text("slotReadUnspecified")) {if isCurrent() {model.choose(.unspecified,expected:control)}}
                                .accessibilityAddTraits(model.resourceMode == .unspecified ? .isSelected:[])
                            if model.linkedResourceAvailable {
                                Button((model.resourceMode == .linked ? "✓ ":"")+AppCopy.text("slotReadLinkedResource")) {if isCurrent() {model.choose(.linked,expected:control)}}
                                    .accessibilityAddTraits(model.resourceMode == .linked ? .isSelected:[])
                            }
                            Button(AppCopy.text("slotReadSubmit")) {Task {if isCurrent() {await model.submit(control)}}}.disabled(!model.canRead)
                        } else if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                        else if let failure=model.failure {
                            Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)
                            Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.retry(control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                            Button(AppCopy.text("slotReadEdit")) {if isCurrent() {model.edit(control)}}
                        } else if let context=model.context,model.read==context.read {
                            if let review=model.review,review.valid(for:context) {
                                Text(AppCopy.text("slotReviewTitle")).font(.headline)
                                LabeledContent(AppCopy.text("business"),value:label(context.business.name,id:context.business.id))
                                LabeledContent(AppCopy.text("service"),value:label(context.service.name,id:context.service.id))
                                LabeledContent(AppCopy.text("referenceResourceTitle"),value:context.resource.map {label($0.name,id:$0.id)} ?? AppCopy.text("slotReadUnspecified"))
                                Text(context.read.intent.day+" · "+context.read.intent.timezone).font(.caption)
                                Text(AppCopy.text("intervalStart")+": "+instant(review.candidate.startAt,zone:context.read.intent.timezone))
                                Text(AppCopy.text("intervalEnd")+": "+instant(review.candidate.endAt,zone:context.read.intent.timezone))
                                Text(AppCopy.text("slotReviewBoundary")).font(.caption)
                                if let bridge=bookingBridge?(control,review),let useBookingCandidate {Button(AppCopy.text("bookingUseCandidateTime")) {if isCurrent() {useBookingCandidate(bridge)}}}
                                Button(AppCopy.text("slotReviewBack")) {if isCurrent() {model.backToCandidates(control)}}
                            } else {
                                Text(context.read.intent.day+" · "+context.read.intent.timezone).font(.caption)
                                if context.read.candidates.isEmpty {Text(AppCopy.text("slotReadEmpty"))}
                                ForEach(Array(context.read.candidates.enumerated()),id:\.offset) {index,value in
                                    VStack(alignment:.leading) {
                                        Text(AppCopy.text("intervalStart")+": "+instant(value.startAt,zone:context.read.intent.timezone))
                                        Text(AppCopy.text("intervalEnd")+": "+instant(value.endAt,zone:context.read.intent.timezone))
                                        Button(AppCopy.text("slotReviewChoose")) {if isCurrent() {model.selectCandidate(index,expected:control)}}.accessibilityLabel(Text(AppCopy.text("slotReviewChoose")+": "+[AppCopy.text("intervalStart")+": "+instant(value.startAt,zone:context.read.intent.timezone),AppCopy.text("intervalEnd")+": "+instant(value.endAt,zone:context.read.intent.timezone)].joined(separator:", ")))
                                    }
                                }
                            }
                            Button(AppCopy.text("slotReadEdit")) {if isCurrent() {model.edit(control)}}
                            Button(AppCopy.text("slotReviewRefresh")) {Task {if isCurrent() {await model.refresh(control)}}}
                        }
                        Button(AppCopy.text("back")) {if isCurrent() {model.close(control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                    }
                }
            }
        }
    }
}
