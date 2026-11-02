import SwiftUI
import CRMCore

struct ClientDraftRoute<Content: View>: View {
    @ObservedObject var model: ClientDraftViewModel
    let context: ClientDraftContext?
    let businessName: String
    let isCurrent:@MainActor ()->Bool
    let content: Content
    init(model: ClientDraftViewModel,context: ClientDraftContext?,businessName: String,isCurrent:@escaping @MainActor ()->Bool,@ViewBuilder content: () -> Content) { self.model=model; self.context=context; self.businessName=businessName; self.isCurrent=isCurrent; self.content=content() }
    var body: some View {
        let selection = model.session.selection,returnControl=model.returnControl
        content.sheet(isPresented: Binding(get:{ isCurrent() && selection != nil && selection?.context == context && model.session.selection == selection },set:{ if !$0 && isCurrent() { model.close(expected:returnControl) } })) {
            if let selection,selection.context == context,model.session.selection == selection,isCurrent() { ClientDraftScreen(model:model,selection:selection,businessName:businessName,isCurrent:isCurrent) }
        }
    }
}
struct ClientDraftEntry:View {
    @ObservedObject var model:ClientDraftViewModel
    let context:ClientDraftContext
    let isCurrent:@MainActor ()->Bool
    let onOpen:@MainActor (ClientDraftEntryControl)->Void
    var body:some View {
        let entry=model.entryControl
        if isCurrent(),let entry,entry.context==context {Button(AppCopy.text("clientDraftTitle")) {if isCurrent() && model.entryControl==entry {onOpen(entry)}}}
    }
}
struct ClientDraftScreen: View {
    @ObservedObject var model: ClientDraftViewModel
    let selection: ClientDraftSelection
    let businessName: String
    @FocusState private var focus: ClientDraftField?
    let isCurrent:@MainActor ()->Bool
    private func submissionKey(_ phase:ClientCreateAttemptPhase)->String {
        switch phase {case .pending:"taskCommentFakePending";case .confirmed:"clientCreateFakeConfirmed";case .rejected:"taskCommentFakeRejected";case .unknown:"taskCommentFakeUnknown"}
    }
    private func value(_ field: ClientDraftField) -> String {
        let v=model.session.values
        switch field { case .fullName: return v.fullName; case .phone: return v.phone; case .email: return v.email; case .source: return v.source; case .notes: return v.notes }
    }
    private func binding(_ field: ClientDraftField,_ input:ClientDraftInputControl?) -> Binding<String> { Binding(get:{isCurrent() && input != nil && model.inputControl==input ? value(field) : ""},set:{if isCurrent() {model.update(field,$0,input:input)}}) }
    private func issue(_ field: ClientDraftField) -> String? {
        guard let problem=model.session.issues.first(where:{$0.field==field})?.problem else { return nil }
        switch problem {
        case .name: return AppCopy.text("clientDraftNameError")
        case .nameLength: return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"255")
        case .phoneLength: return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"32")
        case .email: return AppCopy.text("clientDraftEmailError");case .emailLength:return AppCopy.text("clientDraftMaxLength").replacingOccurrences(of:"{limit}",with:"254");case .characters:return AppCopy.text("taskCancelReasonCharacters")
        case .source: return AppCopy.text("notAvailable")
        }
    }
    private func source(_ raw: String) -> String {
        switch raw { case "parser": return AppCopy.text("clientDraftSourceParser"); case "other": return AppCopy.text("clientDraftSourceOther"); default: return ReadChannelText.label(raw,text:AppCopy.text) }
    }
    var body: some View {
        let control=model.control,input=model.inputControl,returnControl=model.returnControl,question=model.clearConfirmation
        NavigationStack {
            Form {
                if isCurrent(),model.session.selection == selection {
                    Section { LabeledContent(AppCopy.text("business"),value:businessName); Text(AppCopy.text("clientDraftOnly")); Text(AppCopy.text("fixtureMode")).font(.caption) }
                    if model.submissionBlocked {
                        Section {
                            if let record=model.submission {
                                Text(record.attempt.review.preview.fullName)
                                Text(AppCopy.text(submissionKey(record.phase))).accessibilityAddTraits(.updatesFrequently)
                                if record.phase == .confirmed || record.phase == .rejected {Button(AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")) {if isCurrent() {model.acknowledge(expected:control,record:record)}}.accessibilityLabel(Text(AppCopy.text("clientDraftTitle")+": "+AppCopy.text(record.phase == .confirmed ? "taskCommentFakeDone":"taskCommentFakeEdit")))}
                            } else {Text(AppCopy.text("taskCommentFakeQuarantined"))}
                        }
                    } else if model.session.phase == .review,let review=model.session.review,review.selection == selection {
                        Section(AppCopy.text("clientDraftReview")) {
                            LabeledContent(AppCopy.text("clientName"),value:review.preview.fullName)
                            LabeledContent(AppCopy.text("clientPhone"),value:review.preview.phone.isEmpty ? AppCopy.text("notAvailable") : review.preview.phone)
                            LabeledContent(AppCopy.text("clientEmail"),value:review.preview.email.isEmpty ? AppCopy.text("notAvailable") : review.preview.email)
                            LabeledContent(AppCopy.text("clientDraftSource"),value:source(review.preview.source))
                            Text(AppCopy.text("notes")); Text(review.preview.notes)
                        }
                        if let duplicates=model.duplicates {ClientDuplicatePreviewSection(model:duplicates,load:{visit in await model.loadDuplicates(expected:control,visit:visit)},isCurrent:{isCurrent() && model.control == control && model.clearConfirmation == nil})}
                        if model.canSubmit {Button(AppCopy.text("clientCreateFakeSubmit")) {Task {if isCurrent() {await model.submit(review,expected:control)}}}}
                    } else {
                        Section {
                            TextField(AppCopy.text("clientName"),text:binding(.fullName,input)).focused($focus,equals:.fullName).accessibilityHint(issue(.fullName) ?? "")
                            if let error=issue(.fullName) { Text(error).foregroundStyle(.red).accessibilityHidden(true) }
                            #if os(iOS)
                            TextField(AppCopy.text("clientPhone"),text:binding(.phone,input)).keyboardType(.phonePad).focused($focus,equals:.phone).accessibilityHint(issue(.phone) ?? "")
                            #else
                            TextField(AppCopy.text("clientPhone"),text:binding(.phone,input)).focused($focus,equals:.phone).accessibilityHint(issue(.phone) ?? "")
                            #endif
                            if let error=issue(.phone) { Text(error).foregroundStyle(.red).accessibilityHidden(true) }
                            #if os(iOS)
                            TextField(AppCopy.text("clientEmail"),text:binding(.email,input)).keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled().focused($focus,equals:.email).accessibilityHint(issue(.email) ?? "")
                            #else
                            TextField(AppCopy.text("clientEmail"),text:binding(.email,input)).autocorrectionDisabled().focused($focus,equals:.email).accessibilityHint(issue(.email) ?? "")
                            #endif
                            if let error=issue(.email) { Text(error).foregroundStyle(.red).accessibilityHidden(true) }
                            Picker(AppCopy.text("clientDraftSource"),selection:binding(.source,input)) { ForEach(ClientDraftValues.sources,id:\.self) { Text(source($0)).tag($0) } }.accessibilityHint(issue(.source) ?? "")
                            if let error=issue(.source) { Text(error).foregroundStyle(.red).accessibilityHidden(true) }
                            TextField(AppCopy.text("notes"),text:binding(.notes,input),axis:.vertical).lineLimit(4...12).focused($focus,equals:.notes).accessibilityHint(issue(.notes) ?? "")
                            if let error=issue(.notes) {Text(error).foregroundStyle(.red).accessibilityHidden(true)}
                        }
                        Button(AppCopy.text("clientDraftReview")) { if isCurrent() {model.prepare(expected:control);focus=model.session.issues.first?.field} }
                    }
                    if !model.submissionBlocked {Button(AppCopy.text("clientDraftClear"),role:.destructive) { if isCurrent() {model.askClear(expected:control)} }.accessibilityLabel(Text(AppCopy.text("clientDraftTitle")+": "+AppCopy.text("clientDraftClear")))}
                }
            }.navigationTitle(AppCopy.text("clientDraftTitle"))
                .toolbar { ToolbarItem(placement:.cancellationAction) { Button(AppCopy.text("back")) { if isCurrent() {model.back(expected:returnControl)} }.accessibilityLabel(Text(AppCopy.text("clientDraftTitle")+": "+AppCopy.text("back"))) } }
                .sheet(isPresented:Binding(get:{isCurrent() && question != nil && model.clearConfirmation==question},set:{if !$0,let question {model.dismissClear(question)}})) {
                    if let question {ClientDraftClearContent(model:model,question:question,isCurrent:isCurrent)}
                }
        }
    }
}

private struct ClientDraftClearContent:View {
    @ObservedObject var model:ClientDraftViewModel
    let question:ClientDraftClearConfirmation
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        VStack(spacing:20) {
            Text(AppCopy.text("clientDraftClearQuestion")).font(.headline)
            Button(AppCopy.text("clientDraftClear"),role:.destructive) {if isCurrent() {model.confirmClear(question)}}.accessibilityLabel(Text(AppCopy.text("clientDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftClear")))
            Button(AppCopy.text("clientDraftCancel"),role:.cancel) {model.dismissClear(question)}.accessibilityLabel(Text(AppCopy.text("clientDraftTitle")+": "+AppCopy.text("clientDraftClearQuestion")+": "+AppCopy.text("clientDraftCancel")))
        }.padding()
    }
}
