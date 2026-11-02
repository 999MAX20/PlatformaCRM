import SwiftUI
import CRMCore

struct AppointmentReferenceContent:View {
    @ObservedObject var links:AppointmentRelationsViewModel
    let kind:AppointmentReferenceKind
    let isCurrent:@MainActor ()->Bool
    var bookingBridge:(@MainActor (AppointmentSlotControl?,AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl?)? = nil
    var useBookingCandidate:(@MainActor (AppointmentBookingCandidateControl)->Void)? = nil
    var body:some View {
        let presentation=links.presentation
        let readScope=AppCopy.text("appointments")+": "+AppCopy.text(kind == .service ? "service":"referenceResourceTitle")+": "+AppCopy.text("details")
        ScrollView {VStack(alignment:.leading,spacing:12) {
            if isCurrent(),links.matches(presentation) {
                if links.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                else if let failure=links.failure {
                    Text(failure == .notFound ? AppCopy.text("notAvailable"):AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+(failure == .notFound ? AppCopy.text("notAvailable"):AppCopy.error(failure)))).accessibilityAddTraits(.updatesFrequently)
                    Button(AppCopy.text("retry")) {Task {if isCurrent() {await links.retry(presentation:presentation)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                } else if let detail=links.reference {
                    Text(detail.name.isEmpty ? AppCopy.text("notAvailable"):detail.name).font(.headline).textSelection(.enabled)
                    LabeledContent(AppCopy.text("referenceActivityTitle"),value:AppCopy.text(detail.activityCopyKey))
                    if kind == .resource {Text(AppCopy.text(detail.resourceTypeCopyKey))}
                    Text(AppCopy.text("referenceReadOnly")).font(.caption)
                    Text(AppCopy.text("referenceNoBookingProof")).font(.caption)
                    if kind == .service {AppointmentSlotReadContent(model:links.slotReads,isCurrent:{isCurrent() && links.matches(presentation)},bookingBridge:bookingBridge,useBookingCandidate:useBookingCandidate)}
                }
            }
            Spacer(minLength:0)
        }.padding()}.navigationTitle(AppCopy.text(kind == .service ? "service":"referenceResourceTitle"))
    }
}
