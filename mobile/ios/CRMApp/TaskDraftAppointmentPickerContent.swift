import SwiftUI
import CRMCore

struct TaskDraftAppointmentPickerContent:View {
    @ObservedObject var model:TaskDraftViewModel
    @ObservedObject var read:TaskAppointmentPickerViewModel
    let isCurrent:@MainActor ()->Bool
    private func label(_ title:String?,id:Int)->String {(title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(id)"}
    var body:some View {
        let owner=model.appointmentPickerOwner,control=read.control,input=read.inputControl
        let pickerScope=AppCopy.text("taskDraftTitle")+": "+AppCopy.text("taskDraftAppointment")
        let readScope=pickerScope+(read.selectedID == nil ? "" : ": "+AppCopy.text("details"))
        VStack(alignment:.leading,spacing:12) {
            if isCurrent(),model.matchesAppointmentPicker(owner) {
                Text(AppCopy.text("taskDraftAppointment")).font(.headline).accessibilityAddTraits(.isHeader)
                if read.selectedID != nil {
                    if read.detailLoading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {
                        Text(AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure))).accessibilityLabel(Text(readScope+": "+AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure)))).accessibilityAddTraits(.updatesFrequently)
                        Button(AppCopy.text("retry")) {Task {if isCurrent(),model.matchesAppointmentPicker(owner) {await read.retryDetail(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    } else if let choice=read.choice(expected:control) {
                        Text(label(choice.title,id:choice.id))
                        Text(AppCopy.text("status")+": "+choice.status)
                        if let start=choice.startAt {Text(AppCopy.text("intervalStart")+": "+start)}
                        if let end=choice.endAt {Text(AppCopy.text("intervalEnd")+": "+end)}
                        Button(AppCopy.text("taskDraftAppointmentUse")) {if isCurrent() {model.confirmAppointment(owner,read:control)}}
                    }
                    Button(AppCopy.text("back")) {if isCurrent(),model.matchesAppointmentPicker(owner) {read.backDetail(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    TextField(AppCopy.text("taskDraftAppointmentDay"),text:Binding(get:{read.day},set:{if isCurrent(),model.matchesAppointmentPicker(owner) {read.updateDay($0,input:input)}})).disabled(read.loading).accessibilityHint(AppCopy.text("taskDraftAppointmentDayIssue"))
                    if !read.day.isEmpty,!TaskAppointmentDay.valid(read.day) {Text(AppCopy.text("taskDraftAppointmentDayIssue")).foregroundStyle(.red).accessibilityAddTraits(.updatesFrequently)}
                    Button(AppCopy.text("searchSubmit")) {Task {if isCurrent(),model.matchesAppointmentPicker(owner) {await read.read(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(!read.canRead)
                    if read.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=read.failure {Text(AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure))).accessibilityLabel(Text(readScope+": "+AppCopy.text(TaskAppointmentReadFeedback.copyKey(failure)))).accessibilityAddTraits(.updatesFrequently)}
                    else if read.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(read.items.count)).replacingOccurrences(of:"{total}",with:String(read.total))).font(.caption)
                        if read.partial {Text(AppCopy.text("partial"))}
                        if read.items.isEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(read.items) {row in Button(label(row.title,id:row.id)) {Task {if isCurrent(),model.matchesAppointmentPicker(owner) {await read.open(row.id,expected:control)}}}}
                    }
                }
                Button(AppCopy.text("clientDraftCancel")) {if isCurrent() {model.closeAppointmentPicker(owner)}}.accessibilityLabel(Text(pickerScope+": "+AppCopy.text("clientDraftCancel")))
            }
        }
    }
}
