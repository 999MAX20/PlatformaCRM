import SwiftUI
import CRMCore

struct TaskDraftParentPickerContent:View {
    @ObservedObject var model:TaskDraftViewModel
    @ObservedObject var read:TaskParentPickerViewModel
    let isCurrent:@MainActor ()->Bool
    private func label(_ title:String?,id:Int)->String {(title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(id)"}
    var body:some View {
        let owner=model.parentPickerOwner,control=read.control
        let pickerScope=AppCopy.text("taskDraftTitle")+": "+AppCopy.text("taskDraftParent")
        let readScope=pickerScope+(read.selectedID == nil ? "" : ": "+AppCopy.text("details"))
        VStack(alignment:.leading,spacing:12) {
            if isCurrent(),model.matchesParentPicker(owner) {
                Text(AppCopy.text("taskDraftParent")).font(.headline).accessibilityAddTraits(.isHeader)
                if read.selectedID != nil {
                    if read.detailLoading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {
                        Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)
                        Button(AppCopy.text("retry")) {Task {if isCurrent(),model.matchesParentPicker(owner) {await read.retryDetail(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else if let choice=read.choice(expected:control) {
                        Text(label(choice.title,id:choice.id));Text(AppCopy.text("status")+": "+choice.status)
                        Button(AppCopy.text("taskDraftParentUse")) {if isCurrent() {model.confirmParent(owner,read:control)}}
                    }
                    Button(AppCopy.text("back")) {if isCurrent(),model.matchesParentPicker(owner) {read.backDetail(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    Button(AppCopy.text("taskDraftParentLoad")) {Task {if isCurrent(),model.matchesParentPicker(owner) {await read.read(expected:control)}}}.disabled(!read.canRead)
                    if read.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.updatesFrequently)}
                    else if read.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(read.items.count)).replacingOccurrences(of:"{total}",with:String(read.total))).font(.caption)
                        if read.partial {Text(AppCopy.text("partial"))}
                        if read.items.isEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(read.items) {row in Button(label(row.title,id:row.id)) {Task {if isCurrent(),model.matchesParentPicker(owner) {await read.open(row.id,expected:control)}}}}
                    }
                }
                Button(AppCopy.text("clientDraftCancel")) {if isCurrent() {model.closeParentPicker(owner)}}.accessibilityLabel(Text(pickerScope+": "+AppCopy.text("clientDraftCancel")))
            }
        }
    }
}
