import SwiftUI
import CRMCore

struct InboxTaskSourceContent:View {
    @ObservedObject var model:InboxTaskSourceViewModel
    let isCurrent:@MainActor ()->Bool
    private func id(_ value:Int?)->String {value.map {"#\($0)"} ?? AppCopy.text("inboxTaskSourceNone")}
    var body:some View {
        let s=model.session,control=model.control
        let readScope=AppCopy.text("inboxTaskSourceTitle")
        if isCurrent(),s.presented {
            Section(AppCopy.text("inboxTaskSourceTitle")) {
                Text(AppCopy.text("inboxTaskSourceBoundary")).font(.caption)
                Button(AppCopy.text("inboxTaskSourceRead")) {Task {if isCurrent() {await model.read(expected:control)}}}.disabled(!s.canRead)
                if s.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                else if let error=s.failure {Text(AppCopy.error(error)).accessibilityLabel(Text(readScope+": "+AppCopy.error(error))).accessibilityAddTraits(.updatesFrequently)}
                else if let source=s.source {
                    LabeledContent(AppCopy.text("inboxTaskSourceClient"),value:id(source.client));LabeledContent(AppCopy.text("inboxTaskSourceLead"),value:id(source.lead))
                    Button(AppCopy.text("inboxTaskSourceUse")) {if isCurrent() {model.use(expected:control)}}.disabled(!s.canUse)
                }
                if s.choice != nil {Text(AppCopy.text("inboxTaskSourceChosen"));Button(AppCopy.text("inboxTaskSourceClearChoice")) {if isCurrent() {model.clearChoice(expected:control)}}}
            }.disabled(model.controlsBlocked())
        }
    }
}
