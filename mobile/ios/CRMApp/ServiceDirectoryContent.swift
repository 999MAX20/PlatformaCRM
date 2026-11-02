import SwiftUI
import CRMCore

struct ServiceDirectoryAccess:View {
    @ObservedObject var agenda:AgendaViewModel
    @ObservedObject var model:ServiceDirectoryViewModel
    var body:some View {
        let entry=agenda.serviceEntry,child=model.control,presentation=model.presentation
        VStack {
            if entry != nil {Button(AppCopy.text("services")) {Task {await agenda.openServices(expected:entry,child:child)}}}
        }.navigationDestination(isPresented:Binding(get:{model.matchesPresentation(presentation)},set:{if !$0 {agenda.closeServices(expected:presentation)}})) {
            ServiceDirectoryContent(model:model,onClose:{agenda.closeServices(expected:presentation)})
        }
    }
}
struct ServiceDirectoryContent:View {
    @ObservedObject var model:ServiceDirectoryViewModel
    let onClose:@MainActor ()->Void
    var useChoiceLabel:String?=nil
    var useChoice:(@MainActor (ServiceDirectoryReadChoice,ServiceDirectoryControl?)->Void)?=nil
    var isCurrent:@MainActor ()->Bool={true}
    var body:some View {
        let control=model.control
        let readScope=AppCopy.text("services")+(model.selected == nil ? "" : ": "+AppCopy.text("details"))
        Form {
            if let owner=model.owner {Text(owner.scope.business.name)}
            Text(AppCopy.text("serviceWindowBoundary")).font(.caption)
            if model.selected != nil {Button(AppCopy.text("serviceBackToWindow")) {if isCurrent() {model.backToWindow(expected:control)}}}
            if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
            else if let failure=model.failure {
                Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.isStaticText)
                if model.selected==nil {Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.reload(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))}
            } else if let detail=model.detail {
                if detail != model.selected {Text(AppCopy.text("serviceObservedChange")).accessibilityAddTraits(.isStaticText)}
                Section(AppCopy.text("details")) {fields(detail)}
                if let choice=model.choice {
                    Text(AppCopy.text("serviceReadChoice"))
                    Text(choice.item.name)
                    Text(AppCopy.text("serviceReadOnlyBoundary")).font(.caption)
                    if let label=useChoiceLabel,let useChoice {Button(label) {if isCurrent() {useChoice(choice,control)}}}
                } else {Button(AppCopy.text("serviceChooseRead")) {if isCurrent() {model.choose(expected:control)}}}
            } else if let window=model.window {
                Text(AppCopy.text("serviceWindowCount")+": "+String(window.items.count))
                if window.items.isEmpty {Text(AppCopy.text("serviceWindowEmpty"))}
                ForEach(window.items) {row in Button {Task {if isCurrent() {await model.select(row,expected:control)}}} label:{VStack(alignment:.leading) {Text(row.name);Text(AppCopy.text(row.isActive ? "referenceActive":"referenceInactive")).font(.caption)}}}
                Button(AppCopy.text("serviceRefresh")) {Task {if isCurrent() {await model.reload(expected:control)}}}
            }
        }.navigationTitle(AppCopy.text("services"))
        .toolbar {ToolbarItem(placement:.confirmationAction) {Button(AppCopy.text("serviceClose"),action:onClose)}}
    }
    @ViewBuilder private func fields(_ value:ServiceDirectoryItem)->some View {
        Text(value.name)
        if !value.description.isEmpty {Text(value.description)}
        LabeledContent(AppCopy.text("serviceDurationMinutes"),value:String(value.durationMinutes))
        LabeledContent(AppCopy.text("servicePriceFrom"),value:value.priceFrom ?? AppCopy.text("notAvailable"))
        Text(AppCopy.text(value.isActive ? "referenceActive":"referenceInactive"))
    }
}
