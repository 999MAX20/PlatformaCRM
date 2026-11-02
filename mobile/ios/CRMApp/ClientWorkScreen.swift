import SwiftUI
import CRMCore

struct ClientWorkRoute: View {
    @ObservedObject var model: ClientProfileViewModel
    @ObservedObject var work: ClientWorkViewModel
    let business: Business
    let id: Int
    let onRetry: @MainActor () -> Void
    let isCurrent:@MainActor ()->Bool
    private func owns(_ presentation:ClientWorkControl?)->Bool {guard let presentation else {return false};return isCurrent() && work.matches(presentation) && model.readSelection==presentation.selection && presentation.selection.business==business.id && presentation.selection.id==id && model.detail != nil && !model.loading && model.failure==nil}
    var body: some View {
        let presentation=work.presentation
        ClientProfileBody(model:model,business:business,id:id,onRetry:onRetry,isCurrent:isCurrent)
            .navigationDestination(isPresented: Binding(get: {
                owns(presentation) && presentation?.target != nil
            }, set: {if !$0,owns(presentation) {work.back(presentation:presentation)}})) {
                if let presentation,owns(presentation),let target=work.selected {
                    let readScope=AppCopy.text("clients")+": "+AppCopy.text(title(target))+": "+AppCopy.text("details")
                    VStack {
                        if work.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
                        else if let failure = work.failure {
                            Text(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure))))
                            Button(AppCopy.text("retry")) { Task {if owns(presentation) {await work.retry(presentation:presentation)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                        } else if let detail = work.detail { AttentionTargetContent(detail: detail, timezone: business.timezone) }
                    }.navigationTitle(AppCopy.text(title(target)))
                }
            }
    }
    private func title(_ target: ClientWorkTarget) -> String {
        switch target { case .task: "tasks"; case .conversation: "inbox"; case .appointment: "appointments" }
    }
}

struct ClientWorkLinks: View {
    @ObservedObject var work: ClientWorkViewModel
    let timezone: String?
    let isCurrent:@MainActor ()->Bool
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private func window(_ count: Int, _ limit: Int) -> some View {
        Group {
            Text(AppCopy.text("list") + ": \(count) · " + AppCopy.text("windowLimit") + ": \(limit)").font(.caption)
            if count == limit { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
        }
    }
    var body: some View {
        let presentation=work.presentation
        if isCurrent(),let presentation,let parent=work.parent {
            Section(AppCopy.text("tasks")) {
                if let rows = work.tasks {
                    window(rows.count, parent.payload_budget.max_related_per_section)
                    ForEach(rows) { row in Button(value(row.title)) { Task {if isCurrent() {await work.open(.task(row.id),presentation:presentation)}} } }
                } else { Text(AppCopy.text("notAvailable")) }
            }
            Section(AppCopy.text("inbox")) {
                if let rows = work.conversations {
                    window(rows.count, parent.payload_budget.max_related_per_section)
                    ForEach(rows) { row in Button(value(row.title)) { Task {if isCurrent() {await work.open(.conversation(row.id),presentation:presentation)}} } }
                } else { Text(AppCopy.text("notAvailable")) }
            }
            Section(AppCopy.text("appointments")) {
                if let rows = work.appointments {
                    window(rows.count, parent.payload_budget.max_related_per_section)
                    ForEach(rows) { row in
                        Button { Task {if isCurrent() {await work.open(.appointment(row.id),presentation:presentation)}} } label: {
                            VStack(alignment: .leading) {
                                Text(value(row.title)); Text(AppointmentStatusText.label(row.status, text: AppCopy.text)).font(.caption)
                                Text(AppointmentDate.format(startAt: row.start_at, timezone: timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable")).font(.caption)
                            }.foregroundStyle(.primary)
                        }
                    }
                } else { Text(AppCopy.text("notAvailable")) }
            }
        }
    }
}
