import SwiftUI
import CRMCore

struct AppointmentDetailRoute: View {
    @ObservedObject var model: AgendaViewModel
    @ObservedObject var links: AppointmentRelationsViewModel
    let id: Int
    private var current: Bool {links.request != nil && links.request==model.session.detailSelection && model.session.detailSelection?.id==id}
    private func owns(_ presentation:AppointmentRelationControl?)->Bool {guard let presentation else {return false};return current && links.matches(presentation) && model.session.detailSelection==presentation.request}
    var body: some View {
        let presentation=links.presentation,parent=model.control
        let taskScope=AppCopy.text("appointments")+": "+AppCopy.text("tasks")+": "+AppCopy.text("details")
        AppointmentDetailBody(model: model, id: id)
            .navigationDestination(isPresented: Binding(get: {current && links.selected != nil},set: {if !$0,owns(presentation) {links.back(presentation:presentation)}})) {
                if current,let presentation,owns(presentation),let request = links.request, let target = links.selected {
                    switch target {
                    case .client(let clientID):
                        ClientProfileContent(model: links.profile, business: request.scope.business, id: clientID, onRetry:{Task {if owns(presentation) {await links.retry(presentation:presentation)}}},isCurrent:{owns(presentation)})
                            .navigationTitle(AppCopy.text("senderClient"))
                    case .task:
                        VStack {
                            if links.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(taskScope+": "+AppCopy.text("loading"))) }
                            else if let failure = links.failure {
                                Text(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure)).accessibilityLabel(Text(taskScope+": "+(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure))))
                                Button(AppCopy.text("retry")) { Task {if owns(presentation) {await links.retry(presentation:presentation)}} }.accessibilityLabel(Text(taskScope+": "+AppCopy.text("retry")))
                            } else if let task = links.task { AttentionTargetContent(detail: .task(task), timezone: request.scope.business.timezone) }
                        }.navigationTitle(AppCopy.text("tasks"))
                    case .service,.resource:
                        if let kind=target.referenceKind {AppointmentReferenceContent(links:links,kind:kind,isCurrent:{owns(presentation)},bookingBridge:{slot,review in model.bookingCandidateControl(parent:parent,related:presentation,slot:slot,review:review)},useBookingCandidate:{model.useBookingCandidate($0)})}
                    }
                }
            }
    }
}

struct AppointmentRelationLinks: View {
    @ObservedObject var links: AppointmentRelationsViewModel
    let isCurrent:@MainActor ()->Bool
    let onRetryParent: @MainActor () -> Void
    private func title(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    var body: some View {
        let presentation=links.presentation
        let parentScope=AppCopy.text("appointments")+": "+AppCopy.text("details")
        Group {
            if isCurrent(),let presentation,let parent = links.parent {
                Section(AppCopy.text("senderClient")) {
                    if parent.linkedClientID != nil { Button(AppCopy.text("openTarget") + " · " + AppCopy.text("senderClient")) { Task {if isCurrent() {await links.openClient(presentation:presentation)}} } }
                    else {
                        Text(AppCopy.text("notAvailable"))
                        if parent.clientLinkAmbiguous { Label(AppCopy.text("attention"), systemImage: "exclamationmark.triangle") }
                    }
                }
                Section(AppCopy.text("details")) {
                    ForEach(AppointmentReferenceKind.allCases,id:\.rawValue) {kind in
                        if links.referenceAvailable(kind) {Button(AppCopy.text("openTarget")+" · "+AppCopy.text(kind == .service ? "service":"referenceResourceTitle")) {Task {if isCurrent() {await links.openReference(kind,presentation:presentation)}}}}
                    }
                }
                Section(AppCopy.text("tasks")) {
                    if let tasks = links.tasks, let cap = parent.payload_budget?.max_related_per_section {
                        Text(AppCopy.text("list") + ": \(tasks.count) · " + AppCopy.text("windowLimit") + ": \(cap)").font(.caption)
                        if tasks.count == cap { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if tasks.isEmpty { Text(AppCopy.text("noResults")) }
                        ForEach(tasks) { task in Button(title(task.title)) { Task {if isCurrent() {await links.openTask(task.id,presentation:presentation)}} } }
                    } else { Text(AppCopy.text("notAvailable")) }
                }
                Button(AppCopy.text("retry")) {if isCurrent(),links.matches(presentation) {onRetryParent()}}.accessibilityLabel(Text(parentScope+": "+AppCopy.text("retry")))
            }
        }
    }
}
