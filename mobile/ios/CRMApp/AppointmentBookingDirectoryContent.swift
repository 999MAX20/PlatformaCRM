import SwiftUI
import CRMCore

// These are private form-owned directory models. Root Agenda directory routes are separate.
struct AppointmentBookingDirectoryAccess:View {
    @ObservedObject var model:AppointmentBookingViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        let control=model.control,presentation=model.selectorControl,clientOwner=model.clientPickerOwner,clientChild=model.clientChoices?.control
        let serviceChild=model.serviceChoices?.control,resourceChild=model.resourceChoices?.control
        VStack {
            if model.editing {
                if model.clientChoices != nil {Button(AppCopy.text("bookingSelectClient")) {if isCurrent() {model.openClientPicker(expected:control,child:clientChild)}}}
                if model.serviceChoices != nil {Button(AppCopy.text("bookingSelectService")) {Task {if isCurrent() {await model.openSelector(.service,expected:control,serviceChild:serviceChild,resourceChild:resourceChild)}}}}
                if model.resourceChoices != nil {Button(AppCopy.text("bookingSelectResource")) {Task {if isCurrent() {await model.openSelector(.resource,expected:control,serviceChild:serviceChild,resourceChild:resourceChild)}}}}
            }
        }.navigationDestination(isPresented:Binding(get:{model.matchesClientPicker(clientOwner)},set:{if !$0 {model.closeClientPicker(clientOwner)}})) {
            if let search=model.clientChoices {AppointmentBookingClientPickerContent(model:model,search:search,owner:clientOwner,isCurrent:isCurrent)}
        }.navigationDestination(isPresented:Binding(get:{presentation?.kind == .service && model.matchesSelector(presentation)},set:{if !$0,presentation?.kind == .service {model.closeSelector(expected:presentation)}})) {
            if let child=model.serviceChoices {AppointmentBookingServiceDirectory(book:model,model:child,presentation:presentation,isCurrent:isCurrent)}
        }.navigationDestination(isPresented:Binding(get:{presentation?.kind == .resource && model.matchesSelector(presentation)},set:{if !$0,presentation?.kind == .resource {model.closeSelector(expected:presentation)}})) {
            if let child=model.resourceChoices {AppointmentBookingResourceDirectory(book:model,model:child,presentation:presentation,isCurrent:isCurrent)}
        }
    }
}
private struct AppointmentBookingServiceDirectory:View {
    @ObservedObject var book:AppointmentBookingViewModel
    @ObservedObject var model:ServiceDirectoryViewModel
    let presentation:AppointmentBookingDirectoryControl?
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        ServiceDirectoryContent(model:model,onClose:{book.closeSelector(expected:presentation)},useChoiceLabel:AppCopy.text("bookingUseService"),useChoice:{choice,child in if isCurrent() {book.useService(choice,child:child,expected:presentation)}},isCurrent:{isCurrent() && book.matchesSelector(presentation)})
    }
}
private struct AppointmentBookingResourceDirectory:View {
    @ObservedObject var book:AppointmentBookingViewModel
    @ObservedObject var model:ResourceDirectoryViewModel
    let presentation:AppointmentBookingDirectoryControl?
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        ResourceDirectoryContent(model:model,onClose:{book.closeSelector(expected:presentation)},useChoiceLabel:AppCopy.text("bookingUseResource"),useChoice:{choice,child in if isCurrent() {book.useResource(choice,child:child,expected:presentation)}},isCurrent:{isCurrent() && book.matchesSelector(presentation)})
    }
}
