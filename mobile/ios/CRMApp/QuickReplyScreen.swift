import SwiftUI
import CRMCore

struct QuickReplyRoute<Content: View>: View {
    @ObservedObject var model: QuickReplyViewModel
    let parent: ReplyDraftSelection
    let insert: (QuickReplyChoice,QuickReplyControl?) -> Void
    let isCurrent:@MainActor ()->Bool
    let content: ()->Content
    init(model: QuickReplyViewModel,parent: ReplyDraftSelection,insert: @escaping (QuickReplyChoice,QuickReplyControl?) -> Void,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: @escaping () -> Content) {self.model=model;self.parent=parent;self.insert=insert;self.isCurrent=isCurrent;self.content=content}
    var body: some View {
        let selection=model.session.selection,control=model.control
        content().navigationDestination(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.context.draft==parent && model.session.selection==selection},set:{if !$0 && isCurrent() {model.close(expected:control)}})) {
            if let selection,selection.context.draft==parent,model.session.selection==selection,isCurrent() {QuickReplyScreen(model:model,selection:selection,insert:insert,isCurrent:isCurrent)}
        }
    }
}
struct QuickReplyScreen: View {
    @ObservedObject var model: QuickReplyViewModel
    let selection: QuickReplySelection
    let insert: (QuickReplyChoice,QuickReplyControl?) -> Void
    let isCurrent:@MainActor ()->Bool
    @FocusState private var focused: Bool
    var body: some View {
        let control=model.control,input=model.inputControl;let readScope=AppCopy.text("quickReplyTitle")
        VStack(spacing:12) {
            if isCurrent(),model.session.selection==selection {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                TextField(AppCopy.text("quickReplySearch"),text:Binding(get:{model.session.query},set:{if isCurrent() {model.search($0,input:input)}})).textFieldStyle(.roundedBorder).focused($focused)
                if model.session.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                else if let failure=model.session.failure {
                    Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)))
                    Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.retry(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                } else if model.session.loaded {
                    if model.session.partial {Label(AppCopy.text("partial"),systemImage:"exclamationmark.triangle").accessibilityLabel(Text(readScope+": "+AppCopy.text("partial")))}
                    if model.session.showsEmpty {Text(AppCopy.text(model.session.query.isEmpty ? "quickReplyEmpty" : "noResults")).accessibilityLabel(Text(readScope+": "+AppCopy.text(model.session.query.isEmpty ? "quickReplyEmpty" : "noResults")))}
                    List(model.session.choices) {choice in
                        Button {if isCurrent() {insert(choice,control)}} label: {
                            VStack(alignment:.leading,spacing:4) {
                                Text(choice.template.title).font(.headline)
                                Text(choice.template.text)
                                if !choice.template.category.isEmpty {Text(choice.template.category).font(.caption)}
                                Text(choice.template.channel=="all" ? AppCopy.text("quickReplyAllChannels") : ReadChannelText.label(choice.template.channel,text:AppCopy.text)).font(.caption)
                            }.foregroundStyle(.primary)
                        }
                    }.listStyle(.plain)
                }
            }
            Spacer(minLength:0)
        }.padding(.horizontal).navigationTitle(AppCopy.text("quickReplyTitle"))
            .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("clientDraftCancel")) {if isCurrent() {model.close(expected:control)}}}}
            .onAppear {focused=true}
    }
}
