import SwiftUI
import CRMCore

struct TaskDraftClientPickerContent:View {
    @ObservedObject var model:TaskDraftViewModel
    @ObservedObject var search:ClientSearchViewModel
    @ObservedObject var profile:ClientProfileViewModel
    let isCurrent:@MainActor ()->Bool
    init(model:TaskDraftViewModel,search:ClientSearchViewModel,isCurrent:@escaping @MainActor ()->Bool) {self.model=model;self.search=search;self.profile=search.profile;self.isCurrent=isCurrent}
    private func label(_ title:String?,id:Int)->String {(title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(id)"}
    var body:some View {
        let owner=model.clientPickerOwner,control=search.control,input=search.inputControl
        let pickerScope=AppCopy.text("taskDraftTitle")+": "+AppCopy.text("taskDraftClient")
        let readScope=pickerScope+": "+AppCopy.text(search.session.profileSelection == nil ? "clientServerSearch" : "details")
        VStack(alignment:.leading,spacing:12) {
            if isCurrent(),model.matchesClientPicker(owner) {
                Text(AppCopy.text("taskDraftClient")).font(.headline)
                if let selected=search.session.profileSelection {
                    if profile.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=profile.failure {
                        Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)
                        Button(AppCopy.text("retry")) {Task {if isCurrent(),model.matchesClientPicker(owner) {await search.retryProfile(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else if let detail=profile.detail,detail.valid(for:selected.selection.context.business,id:selected.id) {
                        Text(label(detail.client.title,id:detail.client.id))
                        Button(AppCopy.text("taskDraftClientUse")) {if isCurrent() {model.confirmClient(owner,search:control)}}
                    }
                    Button(AppCopy.text("back")) {if isCurrent(),model.matchesClientPicker(owner) {search.backProfile(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    TextField(AppCopy.text("clientSearch"),text:Binding(get:{search.session.query},set:{if isCurrent(),model.matchesClientPicker(owner) {search.update($0,input:input)}}))
                    Button(AppCopy.text("searchSubmit")) {Task {if isCurrent(),model.matchesClientPicker(owner) {await search.submit(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(search.session.loading)
                    if search.session.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=search.session.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)));Button(AppCopy.text("retry")) {Task {if isCurrent(),model.matchesClientPicker(owner) {await search.submit(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))}
                    else if search.session.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(search.session.items.count)).replacingOccurrences(of:"{total}",with:String(search.session.total))).font(.caption)
                        if search.session.partial {Text(AppCopy.text("partial"))}
                        if search.session.showsEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(search.session.items) {client in Button(label(client.title,id:client.id)) {Task {if isCurrent(),model.matchesClientPicker(owner) {await search.openClient(client.id,expected:control)}}}}
                    }
                }
                Button(AppCopy.text("clientDraftCancel")) {if isCurrent() {model.closeClientPicker(owner)}}.accessibilityLabel(Text(pickerScope+": "+AppCopy.text("clientDraftCancel")))
            }
        }
    }
}
