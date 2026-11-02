import SwiftUI
import CRMCore

struct ClientEditRoute<Content: View>: View {
    @ObservedObject var model: ClientEditViewModel
    let context: ClientEditContext?
    let isCurrent: @MainActor ()->Bool
    let content: Content
    init(model: ClientEditViewModel,context: ClientEditContext?,isCurrent: @escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) {self.model=model;self.context=context;self.isCurrent=isCurrent;self.content=content()}
    var body: some View {
        let selection=model.session.selection,control=model.control
        content.sheet(isPresented:Binding(get:{isCurrent() && selection != nil && selection?.context==context && model.session.selection==selection && model.session.available},set:{if !$0 && isCurrent() {model.close(expected:control)}})) {
            if let selection,selection.context==context,model.session.selection==selection,model.session.available,isCurrent() {ClientEditScreen(model:model,selection:selection,isCurrent:isCurrent)}
        }
    }
}
struct ClientEditEntry: View {
    @ObservedObject var model: ClientEditViewModel
    let context: ClientEditContext
    let isCurrent: @MainActor ()->Bool
    var body: some View {
        let entry=model.entryControl,confirmation=model.confirmation
        if isCurrent(),entry?.context==context {
            if model.session.available {Button(AppCopy.text("clientEditTitle")) {if isCurrent() {model.open(expected:entry)}}}
            else {Text(AppCopy.text(model.session.needsReset ? "clientEditOriginChanged" : "clientEditUnavailable")).font(.caption)}
            if model.session.needsReset && model.session.hasStoredChanges {
                Button(AppCopy.text("clientEditCancel"),role:.destructive) {if isCurrent() {model.askDiscard(expected:entry)}}.accessibilityLabel(Text(AppCopy.text("clientEditTitle")+": "+AppCopy.text("clientEditCancel")))
                    .sheet(isPresented:Binding(get:{isCurrent() && confirmation != nil && confirmation?.entry==entry && model.confirmation==confirmation},set:{if !$0,let confirmation {model.dismiss(confirmation)}})) {
                        if let confirmation {ClientEditConfirmationContent(model:model,confirmation:confirmation,isCurrent:isCurrent)}
                    }
            }
        }
    }
}
// Explicit buttons in a sheet keep confirmation consumption independent of the
// system confirmation-dialog dismissal setter, which can run before its action.
private struct ClientEditConfirmationContent: View {
    @ObservedObject var model: ClientEditViewModel
    let confirmation: ClientEditConfirmation
    let isCurrent: @MainActor ()->Bool
    var body: some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientEditCancelQuestion")).font(.headline)
            Button(AppCopy.text("clientEditCancel"),role:.destructive) {if isCurrent() {model.confirm(confirmation)}}.accessibilityLabel(Text(AppCopy.text("clientEditTitle")+": "+AppCopy.text("clientEditCancelQuestion")+": "+AppCopy.text("clientEditCancel")))
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismiss(confirmation)}.accessibilityLabel(Text(AppCopy.text("clientEditTitle")+": "+AppCopy.text("clientEditCancelQuestion")+": "+AppCopy.text("clientDraftCancel")))
        }.padding()
    }
}
struct ClientEditScreen: View {
    @ObservedObject var model: ClientEditViewModel
    let selection: ClientEditSelection
    @FocusState private var focus: ClientDraftField?
    let isCurrent: @MainActor ()->Bool
    private func label(_ field: ClientDraftField) -> String {
        let key=switch field {case .fullName:"clientName";case .phone:"clientPhone";case .email:"clientEmail";case .source:"clientDraftSource";case .notes:"notAvailable"}
        return AppCopy.text(key)
    }
    private func source(_ value: String) -> String {switch value {case "parser":AppCopy.text("clientDraftSourceParser");case "other":AppCopy.text("clientDraftSourceOther");default:ReadChannelText.label(value,text:AppCopy.text)}}
    private func displayed(_ value: String,_ field: ClientDraftField) -> String {value.isEmpty ? AppCopy.text("clientEditEmpty") : (field == .source ? source(value) : value)}
    private func binding(_ field: ClientDraftField,_ input: ClientEditInputControl?) -> Binding<String> {Binding(get:{model.session.values?.value(field) ?? ""},set:{if isCurrent() {model.update(field,$0,input:input)}})}
    private func issue(_ field: ClientDraftField) -> String? {
        guard let problem=model.session.issues.first(where:{$0.field==field})?.problem else {return nil}
        switch problem {case .name:return AppCopy.text("clientDraftNameError");case .nameLength:return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"255");case .phoneLength:return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"32");case .email:return AppCopy.text("clientDraftEmailError");case .emailLength:return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"254");case .characters:return AppCopy.text("taskCancelReasonCharacters");case .source:return AppCopy.text("notAvailable")}
    }
    var body: some View {
        let control=model.control,input=model.inputControl,confirmation=model.confirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection==selection,model.session.available,model.session.values != nil {
                    Section {Text(AppCopy.text("clientDraftOnly"));Text(AppCopy.text("fixtureMode")).font(.caption)}
                    if model.session.phase == .review,let review=model.session.review,review.selection==selection {
                        if review.changed.isEmpty {Text(AppCopy.text("clientEditNoChanges"))}
                        ForEach(review.changed,id:\.self) {field in
                            Section(label(field)) {
                                LabeledContent(AppCopy.text("clientEditOriginal"),value:displayed(review.original.value(field),field))
                                LabeledContent(AppCopy.text("clientEditModified"),value:displayed(review.values.value(field),field))
                            }
                        }
                    } else {
                        Section {
                            TextField(label(.fullName),text:binding(.fullName,input)).focused($focus,equals:.fullName).accessibilityHint(issue(.fullName) ?? "")
                            if let error=issue(.fullName) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            #if os(iOS)
                            TextField(label(.phone),text:binding(.phone,input)).keyboardType(.phonePad).focused($focus,equals:.phone).accessibilityHint(issue(.phone) ?? "")
                            TextField(label(.email),text:binding(.email,input)).keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled().focused($focus,equals:.email).accessibilityHint(issue(.email) ?? "")
                            #else
                            TextField(label(.phone),text:binding(.phone,input)).focused($focus,equals:.phone).accessibilityHint(issue(.phone) ?? "")
                            TextField(label(.email),text:binding(.email,input)).autocorrectionDisabled().focused($focus,equals:.email).accessibilityHint(issue(.email) ?? "")
                            #endif
                            if let error=issue(.phone) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            if let error=issue(.email) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                            Picker(label(.source),selection:binding(.source,input)) {ForEach(ClientDraftValues.sources,id:\.self) {Text(source($0)).tag($0)}}.accessibilityHint(issue(.source) ?? "")
                            if let error=issue(.source) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                        }
                        Button(AppCopy.text("clientDraftReview")) {if isCurrent() {model.prepare(expected:control);focus=model.session.issues.first?.field}}
                    }
                    Button(AppCopy.text("clientEditCancel"),role:.destructive) {if isCurrent() {model.askCancel(expected:control)}}.accessibilityLabel(Text(AppCopy.text("clientEditTitle")+": "+AppCopy.text("clientEditCancel")))
                }
            }.navigationTitle(AppCopy.text("clientEditTitle"))
                .toolbar {ToolbarItem(placement:.cancellationAction) {Button(AppCopy.text("back")) {if isCurrent() {if let confirmation {model.dismiss(confirmation)} else {model.back(expected:control)}}}.accessibilityLabel(Text(AppCopy.text("clientEditTitle")+": "+AppCopy.text("back")))}}
                .sheet(isPresented:Binding(get:{isCurrent() && confirmation != nil && confirmation?.control==control && model.confirmation==confirmation},set:{if !$0,let confirmation {model.dismiss(confirmation)}})) {
                    if let confirmation {ClientEditConfirmationContent(model:model,confirmation:confirmation,isCurrent:isCurrent)}
                }
        }
    }
}
