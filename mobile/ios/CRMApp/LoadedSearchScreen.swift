import SwiftUI
import CRMCore

struct LoadedSearchScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: LoadedSearchViewModel
    let feed: LoadedSearchFeed
    let openSource: (Int) -> Void
    let isCurrentFeed:@MainActor (LoadedSearchFeed)->Bool
    private var current:Bool {feed==model.feed && feed.business==agenda.session.selection?.business.id && feed.epoch==agenda.businessEpoch && isCurrentFeed(feed)}
    private func owns(_ control:LoadedSearchControl?)->Bool {guard let control else {return false};return model.matches(control) && control.feed.business==agenda.session.selection?.business.id && control.feed.epoch==agenda.businessEpoch && isCurrentFeed(control.feed)}
    private func ownsInput(_ input:LoadedSearchInputControl?)->Bool {guard let input else {return false};return model.inputControl==input && input.feed.business==agenda.session.selection?.business.id && input.feed.epoch==agenda.businessEpoch && isCurrentFeed(input.feed)}
    var body: some View {
        let control=current ? model.control:nil
        let input=current ? model.inputControl:nil
        let epoch=agenda.businessEpoch
        let readScope=AppCopy.text("inboxSearch")+": "+AppCopy.text("searchLoadedOnly")
        NavigationStack {
            List {
                Section {
                    Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                    if let business = agenda.session.selection?.business {
                        Picker(AppCopy.text("business"), selection: Binding(get: { business.id }, set: {id in Task {if agenda.session.selection?.business.id==business.id && agenda.businessEpoch==epoch {await agenda.load(business:id)}}})) {
                            ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                        }
                    }
                    Text(AppCopy.text("searchLoadedOnly")).font(.caption)
                    TextField(AppCopy.text("inboxSearch"), text:Binding(get:{current ? model.query:""},set:{if ownsInput(input) {model.search($0,input:input)}})).textFieldStyle(.roundedBorder)
                    Text(AppCopy.text("searchOrder")).font(.caption)
                }
                if current {
                    ForEach(feed.sources, id: \.kind) { source in
                        Section(AppCopy.text(source.kind.rawValue)) {
                            Text(AppCopy.text(model.coverage(source).rawValue))
                            if let day = source.token?.day { Text(day).font(.caption) }
                            Button(AppCopy.text("openTarget") + " · " + AppCopy.text(source.kind.rawValue)) {if owns(control),let tab=model.sourceTab(source.kind,expected:control) {openSource(tab)}}
                            ForEach(model.matches.filter { $0.id.kind == source.kind }) { hit in
                                Button { Task {if owns(control) {await model.open(hit,expected:control)}} } label: {
                                    VStack(alignment: .leading) { Text(hit.title); Text(AppCopy.text(hit.id.kind.rawValue) + " · #\(hit.id.id)").font(.caption) }.foregroundStyle(.primary)
                                }
                            }
                        }
                    }
                    if model.showsNoMatches { Text(AppCopy.text("searchNoMatches")) }
                } else { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
            }
            .navigationTitle(AppCopy.text("inboxSearch"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selected != nil }, set: {if !$0,owns(control) {model.back(expected:control)}})) {
                if current,let control,let hit = model.selected, let business = agenda.session.selection?.business, business.id == hit.id.business {
                    LoadedSearchDetailScreen(model:model,hit:hit,business:business,control:control,isCurrent:{owns(control)})
                }
            }
        }
    }
}

private struct LoadedSearchDetailScreen: View {
    @ObservedObject var model: LoadedSearchViewModel
    let hit: LoadedSearchHit
    let business: Business
    let control:LoadedSearchControl
    let isCurrent:@MainActor ()->Bool
    var body: some View {
        let readScope=AppCopy.text("inboxSearch")+": "+AppCopy.text("searchLoadedOnly")+": "+AppCopy.text("details")
        Group {
            if !isCurrent() {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
            else if hit.id.kind == .clients {
                ClientProfileContent(model: model.profile, business: business, id: hit.id.id, onRetry: { Task {if isCurrent() {await model.retry(expected:control)}} },isCurrent:isCurrent)
            } else if model.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.failure {
                VStack {
                    Text(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+(failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure))))
                    Button(AppCopy.text("retry")) { Task {if isCurrent() {await model.retry(expected:control)}} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                }
            } else if let detail = model.detail { AttentionTargetContent(detail: detail, timezone: business.timezone) }
        }.navigationTitle(AppCopy.text(hit.id.kind.rawValue))
    }
}
