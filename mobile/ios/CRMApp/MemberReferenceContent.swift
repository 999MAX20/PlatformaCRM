import SwiftUI
import CRMCore

struct MemberReferenceContent:View {
    @ObservedObject var model:MemberReferenceViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        let s=model.session,control=model.control,input=s.input
        let readScope=AppCopy.text("memberReferenceTitle")
        if isCurrent(),s.presented {
            Section(AppCopy.text("memberReferenceTitle")) {
                Text(AppCopy.text("memberReferenceReadOnly")).font(.caption)
                TextField(AppCopy.text("memberReferenceIdentifier"),text:Binding(get:{model.session.rawInput},set:{if isCurrent() {model.update($0,input:input)}}))
                    .accessibilityHint(s.invalidIdentifier ? AppCopy.text("memberReferenceInvalid") : "")
                if s.invalidIdentifier {Text(AppCopy.text("memberReferenceInvalid")).accessibilityHidden(true)}
                Button(AppCopy.text("memberReferenceRead")) {Task {if isCurrent() {await model.read(expected:control)}}}.disabled(!s.canRead)
                Button(AppCopy.text("searchClear")) {if isCurrent() {model.clear(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchClear")))
                if s.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                else if let error=s.failure {Text(AppCopy.error(error)).accessibilityLabel(Text(readScope+": "+AppCopy.error(error))).accessibilityAddTraits(.updatesFrequently)}
                else if let source=s.source {
                    Text((source.user.displayName ?? AppCopy.text("notAvailable"))+" · #\(source.id)");Text(source.user.email)
                    Text(AppCopy.text(source.isActive ? "memberReferenceActive":"memberReferenceInactive"))
                    Button(AppCopy.text("memberReferenceUse")) {if isCurrent() {model.use(expected:control)}}.disabled(!s.canUse)
                }
                if let choice=s.choice {LabeledContent(AppCopy.text("memberReferenceChosen"),value:choice.source.user.displayName ?? AppCopy.text("notAvailable"));Button(AppCopy.text("memberReferenceClearChoice")) {if isCurrent() {model.clearChoice(expected:control)}}}
            }.disabled(model.controlsBlocked())
        }
    }
}
