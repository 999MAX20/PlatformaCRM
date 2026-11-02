import SwiftUI
import CRMCore

struct ClientSearchRoute<Content: View>: View {
    @ObservedObject var model: ClientSearchViewModel
    let business: Business
    let context: ClientSearchContext
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: ClientSearchViewModel,business: Business,context: ClientSearchContext,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) {self.model=model;self.business=business;self.context=context;self.isCurrent=isCurrent;self.content=content()}
    var body: some View {
        let selection=model.session.selection
        let control=model.control
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.context==context && model.session.selection==selection},set:{if !$0,isCurrent() {model.close(expected:control)}})) {
            if isCurrent(),let selection,selection.context==context,model.session.selection==selection {ClientSearchScreen(model:model,business:business,selection:selection,isCurrent:isCurrent)}
        }
    }
}
struct ClientSearchScreen: View {
    @ObservedObject var model: ClientSearchViewModel
    let business: Business
    let selection: ClientSearchSelection
    let isCurrent:@MainActor ()->Bool
    private func owns(_ control:ClientSearchControl?)->Bool {control?.selection==selection && model.matches(control) && isCurrent()}
    private func ownsInput(_ input:ClientSearchInputControl?)->Bool {input?.selection==selection && model.inputControl==input && isCurrent()}
    private func value(_ raw: String?) -> String {guard let raw,!raw.isEmpty else {return AppCopy.text("notAvailable")};return raw}
    private var countText: String {AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(model.session.items.count)).replacingOccurrences(of:"{total}",with:String(model.session.total))}
    var body: some View {
        let profileSelection=model.session.profileSelection
        let control=model.control,input=model.inputControl
        let readScope=AppCopy.text("clients")+": "+AppCopy.text("clientServerSearch")
        NavigationStack {
            VStack(spacing:12) {
                if isCurrent(),model.session.selection==selection {
                    Label(AppCopy.text("fixtureMode"),systemImage:"testtube.2").font(.caption)
                    LabeledContent(AppCopy.text("business"),value:business.name)
                    TextField(AppCopy.text("clientSearch"),text:Binding(get:{model.session.query},set:{if ownsInput(input) {model.update($0,input:input)}})).textFieldStyle(.roundedBorder)
                        .onSubmit {Task {if owns(control) {await model.submit(expected:control)}}}
                    HStack {
                        Button(AppCopy.text("searchSubmit")) {Task {if owns(control) {await model.submit(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(model.session.loading)
                        Button(AppCopy.text("searchClear")) {if owns(control) {model.clear(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchClear")))
                    }
                    if model.session.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=model.session.failure {
                        Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)
                        Button(AppCopy.text("retry")) {Task {if owns(control) {await model.submit(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else if model.session.loaded {
                        Text(countText).font(.caption)
                        if model.session.partial {Label(AppCopy.text("partial"),systemImage:"exclamationmark.triangle")}
                        if model.session.showsEmpty {Text(AppCopy.text(model.session.submitted?.isEmpty==true ? "clientsEmpty" : "noResults"))}
                        List(model.session.items) {client in
                            Button {Task {if owns(control) {await model.openClient(client.id,expected:control)}}} label: {
                                VStack(alignment:.leading,spacing:4) {Text(value(client.title));Text("\(AppCopy.text("clientPhone")): \(value(client.phone))").font(.caption)}.foregroundStyle(.primary)
                            }
                        }.listStyle(.plain)
                    }
                }
                Spacer(minLength:0)
            }.padding(.horizontal).navigationTitle(AppCopy.text("clientServerSearch"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if owns(control) {model.close(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))}}
                .environment(\.locale,Locale(identifier:AppCopy.language))
                .navigationDestination(isPresented:Binding(get:{isCurrent() && model.session.selection==selection && profileSelection != nil && model.session.profileSelection==profileSelection},set:{if !$0,owns(control) {model.backProfile(expected:control)}})) {
                    if owns(control),let profileSelection,model.session.profileSelection==profileSelection {
                        ClientProfileContent(model:model.profile,business:business,id:profileSelection.id,onRetry:{Task {if owns(control) {await model.retryProfile(expected:control)}}},isCurrent:{owns(control) && model.session.profileSelection==profileSelection}).navigationTitle(AppCopy.text("clients"))
                    }
                }
        }
    }
}
