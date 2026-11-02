import SwiftUI
import CRMCore

struct AttentionQueueScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: AttentionQueueViewModel
    private var business: Int? { agenda.session.selection?.business.id }
    private var current: Bool { model.business == business && model.scopeEpoch==agenda.businessEpoch }
    private func owns(_ control:AttentionControl?)->Bool {guard let control else {return false};return model.matches(control) && agenda.session.selection?.business.id==control.business && agenda.businessEpoch==control.epoch}
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private func kind(_ item: AttentionItem) -> String {
        switch item.readTarget?.kind { case .task: AppCopy.text("tasks"); case .conversation: AppCopy.text("inbox"); case .appointment: AppCopy.text("appointments"); case nil: AppCopy.text("notAvailable") }
    }
    private func error(_ failure: ReadFailure) -> String { failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure) }
    private func row(_ item: AttentionItem) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value(item.entity.title)); Text(kind(item)).font(.caption)
            Text(AppCopy.text("openTarget") + ": " + AppCopy.text(item.readTarget == nil ? "notAvailable" : "readOnly")).font(.caption)
        }.foregroundStyle(.primary).accessibilityElement(children: .combine)
    }
    var body: some View {
        let epoch=agenda.businessEpoch
        let ownerBusiness=business
        let control=current ? model.control:nil
        let readScope=AppCopy.text("attention"),bootstrapScope=AppCopy.text("attention")+": "+AppCopy.text("business")
        NavigationStack {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                Text(AppCopy.text("readOnly")).font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business }, set: {id in Task {if agenda.session.selection?.business.id==business && agenda.businessEpoch==epoch {await agenda.load(business:id)}}})) {
                        ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                    }
                }
                if business == nil, let failure = agenda.failure {
                    Text(error(failure)).accessibilityLabel(Text(bootstrapScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else if business == nil || !current || model.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
                else {
                    TextField(AppCopy.text("inboxSearch"), text:Binding(get:{model.query},set:{if owns(control) {model.search($0,expected:control)}})).textFieldStyle(.roundedBorder)
                    if let failure = model.failure { Text(error(failure)).accessibilityLabel(Text(readScope+": "+error(failure))) }
                    else if model.loaded {
                        Text(AppCopy.text("list") + ": \(model.items.count) · " + AppCopy.text("windowLimit") + ": \(model.limit)").font(.caption)
                        if model.windowCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if model.showsEmpty { Text(AppCopy.text("noResults")) }
                        List(model.visible) { item in
                            if item.readTarget != nil { Button { Task {if owns(control) {await model.open(item.id,expected:control)}} } label: { row(item) } }
                            else { row(item) }
                        }.listStyle(.plain)
                    }
                    Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retryList(expected:control)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal).navigationTitle(AppCopy.text("attention"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selectedID != nil }, set: {if !$0,owns(control) {model.back(expected:control)}})) { if current { targetContent } }
            .task(id: "\(ownerBusiness ?? 0):\(epoch)") {if agenda.session.selection?.business.id==ownerBusiness,agenda.businessEpoch==epoch,!current || (!model.loaded && !model.loading && model.failure == nil) {await model.load(business:ownerBusiness,epoch:epoch)}}
        }
    }
    private var targetContent: some View {
        let control=current ? model.control:nil
        let detailScope=AppCopy.text("attention")+": "+AppCopy.text("details")
        return VStack {
            if model.detailLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(detailScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.detailFailure, let identity = model.selectedID {
                Text(error(failure)).accessibilityLabel(Text(detailScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retryDetail(expected:control)}} }.accessibilityLabel(Text(detailScope+": "+AppCopy.text("retry")))
            } else if let detail = model.detail { AttentionTargetContent(detail: detail, timezone: agenda.session.selection?.business.timezone) }
        }.navigationTitle(AppCopy.text("details"))
    }
}
