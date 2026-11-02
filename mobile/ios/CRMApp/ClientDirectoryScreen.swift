import SwiftUI
import CRMCore

struct ClientDirectoryScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: ClientDirectoryViewModel
    @ObservedObject var profile: ClientProfileViewModel
    var isActive = true
    private var business: Int? { agenda.session.selection?.business.id }
    private var current: Bool { model.business == business && model.scopeEpoch == agenda.businessEpoch }
    private func value(_ raw: String?) -> String {
        guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }
        return raw
    }
    var body: some View {
        let control=model.control
        ClientDraftRoute(model:model.draft,context:agenda.session.selection.map { ClientDraftContext(business:$0.business.id,epoch:agenda.businessEpoch) },businessName:agenda.session.selection?.business.name ?? AppCopy.text("notAvailable"),isCurrent:{owns(control) && model.selectedID==nil && model.serverSearch?.session.selection==nil}) {
            if current,let search=model.serverSearch,let business=agenda.session.selection?.business {
                ClientSearchRoute(model:search,business:business,context:ClientSearchContext(business:business.id,epoch:agenda.businessEpoch),isCurrent:{owns(control) && model.draft.control==nil && model.selectedID==nil}) {directoryContent}
            } else {directoryContent}
        }
    }
    private func owns(_ control:ClientDirectoryControl?) -> Bool {
        guard let control else {return false}
        return model.matches(control) && agenda.session.selection?.business.id==control.business && agenda.businessEpoch==control.epoch
    }
    private var directoryContent: some View {
        let control=model.control,list=model.listControl
        let readScope=AppCopy.text("clients"),bootstrapScope=AppCopy.text("clients")+": "+AppCopy.text("business")
        let overlayVisit=profile.localOverlayVisit,mergeReturn=profile.merge?.control
        return NavigationStack {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business }, set: { id in Task { await agenda.load(business: id) } })) {
                        ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                    }
                }
                if business == nil, let failure = agenda.failure {
                    Text(AppCopy.error(failure)).accessibilityLabel(Text(bootstrapScope+": "+AppCopy.error(failure)))
                    Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else if business == nil || !current || model.loading {
                    ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))
                } else {
                    if model.serverSearch != nil {Button(AppCopy.text("clientServerSearch")) {if owns(control),model.openSearch(list:list) {profile.clear()}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("clientServerSearch")))}
                    TextField(AppCopy.text("clientSearch"), text: Binding(get:{model.query},set:{if owns(control) {model.search($0,list:list)}})).textFieldStyle(.roundedBorder)
                    if let failure = model.failure {
                        Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)))
                        Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retry(list:list)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else {
                        if model.loaded,let business {
                            ClientDraftEntry(model:model.draft,context:ClientDraftContext(business:business,epoch:agenda.businessEpoch),isCurrent:{owns(control) && model.matchesList(list)},onOpen:{entry in if model.openDraft(expected:entry,list:list) {profile.clear()}})
                        }
                        if model.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if model.showsEmpty { Text(AppCopy.text(model.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "clientsEmpty" : "noResults")) }
                        if model.visible.isEmpty {
                            Button(AppCopy.text("retry")) { Task {if owns(control) {await model.retry(list:list)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                        }
                        List(model.visible) { client in
                            Button {if owns(control),model.open(id:client.id,list:list) {profile.clear()}} label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(value(client.title))
                                    Text("\(AppCopy.text("clientPhone")): \(value(client.phone))").font(.caption)
                                }.foregroundStyle(.primary)
                            }
                        }.listStyle(.plain)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal)
            .navigationTitle(AppCopy.text("clients"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selected != nil }, set: {if !$0,owns(control),profile.localOverlayVisit==overlayVisit {if !profile.closeMerge(expected:mergeReturn),profile.merge?.context==nil,model.back(expected:control) {profile.clear()}}})) {
                if current, let client = model.selected, let selectedBusiness = agenda.session.selection?.business {
                    ClientProfileScreen(model: profile, business: selectedBusiness, id: client.id, epoch:agenda.businessEpoch,isCurrent:{owns(control)},onContact:{business,contact in if owns(control) {model.refreshContact(business:business,contact:contact,expected:control)}})
                }
            }
            .task(id: "\(business ?? 0):\(agenda.businessEpoch):\(isActive)") {
                guard isActive else { return }
                if !current || (!model.loaded && !model.loading && model.failure == nil) { await model.load(business: business, epoch: agenda.businessEpoch) }
            }
        }
    }
}
