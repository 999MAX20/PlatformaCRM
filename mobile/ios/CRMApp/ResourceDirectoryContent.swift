import SwiftUI
import CRMCore

struct ResourceDirectoryAccess:View {
    @ObservedObject var agenda:AgendaViewModel
    @ObservedObject var model:ResourceDirectoryViewModel
    var body:some View {
        let entry=agenda.resourceEntry,child=model.control,presentation=model.presentation
        VStack {
            if entry != nil {Button(AppCopy.text("resources")) {Task {await agenda.openResources(expected:entry,child:child)}}}
        }.navigationDestination(isPresented:Binding(get:{model.matchesPresentation(presentation)},set:{if !$0 {agenda.closeResources(expected:presentation)}})) {
            ResourceDirectoryContent(model:model,onClose:{agenda.closeResources(expected:presentation)})
        }
    }
}
struct ResourceDirectoryContent:View {
    @ObservedObject var model:ResourceDirectoryViewModel
    let onClose:@MainActor ()->Void
    var useChoiceLabel:String?=nil
    var useChoice:(@MainActor (ResourceDirectoryReadChoice,ResourceDirectoryControl?)->Void)?=nil
    var isCurrent:@MainActor ()->Bool={true}
    var body:some View {
        let control=model.control
        let readScope=AppCopy.text("resources")+(model.selected == nil ? "" : ": "+AppCopy.text("details"))
        Form {
            if let owner=model.owner {Text(owner.scope.business.name)}
            Text(AppCopy.text("resourceDirectoryWindowBoundary")).font(.caption)
            if model.selected != nil {Button(AppCopy.text("resourceDirectoryBackToWindow")) {if isCurrent() {model.backToWindow(expected:control)}}}
            if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
            else if let failure=model.failure {
                Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.isStaticText)
                if model.selected==nil {Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.reload(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))}
            } else if let detail=model.detail {
                if detail != model.selected {Text(AppCopy.text("resourceDirectoryObservedChange")).accessibilityAddTraits(.isStaticText)}
                Section(AppCopy.text("details")) {fields(detail)}
                if let choice=model.choice {
                    Text(AppCopy.text("resourceDirectoryReadChoice"))
                    Text(choice.item.name)
                    Text(AppCopy.text("resourceDirectoryReadOnlyBoundary")).font(.caption)
                    if let label=useChoiceLabel,let useChoice {Button(label) {if isCurrent() {useChoice(choice,control)}}}
                } else {Button(AppCopy.text("resourceDirectoryChooseRead")) {if isCurrent() {model.choose(expected:control)}}}
            } else if let window=model.window {
                Text(AppCopy.text("resourceDirectoryWindowCount")+": "+String(window.items.count))
                if window.items.isEmpty {Text(AppCopy.text("resourceDirectoryWindowEmpty"))}
                ForEach(window.items) {row in Button {Task {if isCurrent() {await model.select(row,expected:control)}}} label:{VStack(alignment:.leading) {Text(row.name);Text(AppCopy.text(row.isActive ? "referenceActive":"referenceInactive")).font(.caption)}}}
                Button(AppCopy.text("resourceDirectoryRefresh")) {Task {if isCurrent() {await model.reload(expected:control)}}}
            }
        }.navigationTitle(AppCopy.text("resources"))
        .toolbar {ToolbarItem(placement:.confirmationAction) {Button(AppCopy.text("resourceDirectoryClose"),action:onClose)}}
    }
    @ViewBuilder private func fields(_ value:ResourceDirectoryItem)->some View {
        Text(value.name)
        LabeledContent(AppCopy.text("resourceDirectoryType"),value:AppCopy.text(value.hasKnownType ? value.typeCopyKey:"resourceDirectoryTypeUnknown"))
        Text(AppCopy.text(value.isActive ? "referenceActive":"referenceInactive"))
    }
}
