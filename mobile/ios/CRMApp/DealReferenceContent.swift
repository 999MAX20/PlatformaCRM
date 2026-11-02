import SwiftUI
import CRMCore

struct DealReferenceContent:View {
    @ObservedObject var model:DealReferenceViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        let s=model.session,control=model.control,input=s.input
        let readScope=AppCopy.text("dealReferenceTitle")
        if isCurrent(),s.presented {
            Section(AppCopy.text("dealReferenceTitle")) {
                Text(AppCopy.text("dealReferenceReadOnly")).font(.caption)
                TextField(AppCopy.text("dealReferenceIdentifier"),text:Binding(get:{model.session.rawInput},set:{if isCurrent() {model.update($0,input:input)}}))
                    .accessibilityHint(s.invalidIdentifier ? AppCopy.text("dealReferenceInvalid") : "")
                if s.invalidIdentifier {Text(AppCopy.text("dealReferenceInvalid")).accessibilityHidden(true)}
                Button(AppCopy.text("dealReferenceRead")) {Task {if isCurrent() {await model.read(expected:control)}}}.disabled(!s.canRead)
                Button(AppCopy.text("searchClear")) {if isCurrent() {model.clear(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchClear")))
                if s.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                else if let error=s.failure {Text(AppCopy.error(error)).accessibilityLabel(Text(readScope+": "+AppCopy.error(error))).accessibilityAddTraits(.updatesFrequently)}
                else if let source=s.source {
                    Text(source.title+" · #\(source.id)");LabeledContent(AppCopy.text("dealReferenceClient"),value:"#\(source.client)")
                    LabeledContent(AppCopy.text("dealReferenceLead"),value:source.lead.map {"#\($0)"} ?? AppCopy.text("inboxLeadNone"))
                    Button(AppCopy.text("dealReferenceUse")) {if isCurrent() {model.use(expected:control)}}.disabled(!s.canUse)
                }
                if let choice=s.choice {LabeledContent(AppCopy.text("dealReferenceChosen"),value:choice.source.title+" · #\(choice.source.id)");Button(AppCopy.text("dealReferenceClearChoice")) {if isCurrent() {model.clearChoice(expected:control)}}}
            }.disabled(model.controlsBlocked())
        }
    }
}
