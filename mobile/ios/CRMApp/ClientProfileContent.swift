import SwiftUI
import CRMCore

struct ClientProfileContent: View {
    @ObservedObject var model: ClientProfileViewModel
    let business: Business
    let id: Int
    let onRetry: @MainActor () -> Void
    let isCurrent:@MainActor ()->Bool
    var body: some View {
        let read=model.readSelection,workPresentation=model.work?.presentation,overlayVisit=model.localOverlayVisit
        let readScope=AppCopy.text("clients")+": "+AppCopy.text("details")
        if !isCurrent() {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
        else if let edit=model.edit {
            ClientEditRoute(model:edit,context:model.business==business.id && model.id==id ? model.scopeEpoch.map {ClientEditContext(business:business.id,client:id,epoch:$0)} : nil,isCurrent:{isCurrent() && model.localOverlayVisit==overlayVisit && model.merge?.context==nil && model.readSelection==read && model.work?.presentation==workPresentation && workPresentation?.target==nil && model.detail != nil && !model.loading && model.failure==nil}) {profileContent}
        } else {profileContent}
    }
    @ViewBuilder private var profileContent: some View {
        if let work=model.work {ClientWorkRoute(model:model,work:work,business:business,id:id,onRetry:onRetry,isCurrent:isCurrent)}
        else {ClientProfileBody(model:model,business:business,id:id,onRetry:onRetry,isCurrent:isCurrent)}
    }
}

struct ClientProfileBody: View {
    @ObservedObject var model: ClientProfileViewModel
    let business: Business
    let id: Int
    let onRetry: @MainActor () -> Void
    let isCurrent:@MainActor ()->Bool
    private var current:Bool {isCurrent() && model.business==business.id && model.id==id}
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    var body: some View {
        let read=model.readSelection,workPresentation=model.work?.presentation,overlayVisit=model.localOverlayVisit
        let readScope=AppCopy.text("clients")+": "+AppCopy.text("details")
        VStack {
            if !current || model.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.failure {
                VStack { Text(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure)))); Button(AppCopy.text("retry")) {if current && !model.loading && model.readSelection==read {onRetry()}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
            } else if let detail = model.detail {
                Form {
                    Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                    if let edit=model.edit,let epoch=model.scopeEpoch {ClientEditEntry(model:edit,context:ClientEditContext(business:business.id,client:id,epoch:epoch),isCurrent:{current && model.localOverlayVisit==overlayVisit && model.merge?.context==nil && model.readSelection==read && model.work?.presentation==workPresentation && workPresentation?.target==nil && model.detail != nil && !model.loading && model.failure==nil})}
                    LabeledContent(AppCopy.text("clientName"), value: value(detail.client.title))
                    LabeledContent(AppCopy.text("clientPhone"), value: value(detail.client.phone))
                    LabeledContent(AppCopy.text("clientEmail"), value: value(detail.client.email))
                    Section(AppCopy.text("notes")) { Text(value(detail.details.notes)) }
                    if let merge=model.merge {ClientMergePreviewSection(owner:model,model:merge,isCurrent:{current && model.readSelection==read})}
                    if let work = model.work { ClientWorkLinks(work:work,timezone:business.timezone,isCurrent:{current && model.localOverlayVisit==overlayVisit && model.merge?.context==nil && model.readSelection==read && work.selection==read && model.edit?.session.selection==nil && model.edit?.confirmation==nil && model.detail != nil && !model.loading && model.failure==nil}) }
                    else if !detail.related.appointments.isEmpty {
                        Section(AppCopy.text("appointments")) {
                            if detail.historyCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                            ForEach(detail.related.appointments, id: \.appointment.id) { visit in
                                VStack(alignment: .leading) {
                                    Text(value(visit.appointment.title)); Text(AppointmentStatusText.label(visit.appointment.status, text: AppCopy.text)).font(.caption)
                                    Text(AppointmentDate.format(startAt: visit.appointment.start_at, timezone: business.timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable")).font(.caption)
                                }
                            }
                        }
                    }
                }
            } else { Button(AppCopy.text("retry")) {if current && !model.loading && model.readSelection==read {onRetry()}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
        }
        .navigationTitle(AppCopy.text("details"))
    }
}
