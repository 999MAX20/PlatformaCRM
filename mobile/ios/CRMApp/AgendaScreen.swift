import SwiftUI
import CRMCore

struct AgendaScreen: View {
    @StateObject var model: AgendaViewModel
    private var selectedID: Int { model.session.selection?.business.id ?? model.session.businesses.first?.id ?? 0 }
    var body: some View {
        let control=model.control,previousMode=model.mode,previousDate=model.date
        let readScope=AppCopy.text("appointments")
        NavigationStack() {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2")
                    .font(.caption).accessibilityAddTraits(.isStaticText)
                if !model.session.businesses.isEmpty {
                    Picker(AppCopy.text("business"), selection: Binding(get: { selectedID }, set: { id in Task {await model.switchBusiness(id,expected:control)} })) {
                        ForEach(model.session.businesses) { Text($0.name).tag($0.id) }
                    }
                    Picker(AppCopy.text("appointments"), selection:Binding(get:{model.mode},set:{model.setMode($0,previous:previousMode,expected:control)})) {
                        Text(AppCopy.text("list")).tag(AgendaMode.list)
                        Text(AppCopy.text("calendar")).tag(AgendaMode.calendar)
                    }.pickerStyle(.segmented)
                    DatePicker(AppCopy.text("date"),selection:Binding(get:{model.date},set:{next in Task {await model.changeDate(next,previous:previousDate,expected:control)}}),displayedComponents:.date).datePickerStyle(.compact).id(control.generation)
                    if let services=model.services {ServiceDirectoryAccess(agenda:model,model:services)}
                    if let resources=model.resources {ResourceDirectoryAccess(agenda:model,model:resources)}
                    if let selection = model.session.selection {
                        Text(AppCopy.text("date") + ": " + selection.day + " · " + AppCopy.text("timeZone") + ": " + selection.business.timezone).font(.caption)
                    }
                }
                if model.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
                else if let failure = model.failure {
                    Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))).accessibilityAddTraits(.isStaticText)
                    Button(AppCopy.text("retry")) { Task {await model.retryList(expected:control)} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                } else {
                    if model.session.sourceDayMismatch {
                        Label(AppCopy.text("agendaSourceDayMismatch"), systemImage: "exclamationmark.triangle")
                        if let responseDay = model.session.responseDay { Text(AppCopy.text("date") + ": " + responseDay).font(.caption) }
                    }
                    if model.session.isPartial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                    if model.session.isPartial || model.session.sourceDayMismatch {
                        Button(AppCopy.text("retry")) { Task {await model.retryList(expected:control)} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    }
                    if model.session.items.isEmpty {
                        if model.showsEmptyResult {
                            ContentUnavailableView(AppCopy.text("empty"), systemImage: "calendar")
                        }
                        if model.session.selection != nil && !model.session.isPartial && !model.session.sourceDayMismatch {
                            Button(AppCopy.text("retry")) { Task {await model.retryList(expected:control)} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                        }
                    } else if let selection = model.session.selection {
                        AgendaDayContent(display: AgendaDayDisplay(items: model.session.items, day: selection.day, responseDay: model.session.responseDay, timezone: selection.business.timezone), mode: model.mode, timezone: selection.business.timezone, onOpen:{id in Task {await model.openDetail(id:id,expected:control)}})
                    }
                }
            }
            .padding(.horizontal)
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .environment(\.timeZone, TimeZone(identifier: model.session.selection?.business.timezone ?? "UTC") ?? .gmt)
            .navigationTitle(AppCopy.text("appointments"))
            .navigationDestination(isPresented: Binding(get: { model.session.detailSelection != nil }, set: {if !$0 {model.closeDetail(expected:control)}})) {
                if let id = model.session.detailSelection?.id { AppointmentDetailScreen(model: model, id: id) }
            }
            .task { await model.start() }
        }.tint(Color(red: 217 / 255, green: 103 / 255, blue: 24 / 255))
    }
}
struct AppointmentDetailScreen: View {
    @ObservedObject var model: AgendaViewModel
    let id: Int
    var body: some View {
        if let relations = model.relations { AppointmentDetailRoute(model: model, links: relations, id: id) }
        else { AppointmentDetailBody(model: model, id: id) }
    }
}
struct AppointmentDetailBody: View {
    @ObservedObject var model: AgendaViewModel
    let id: Int
    var body: some View {
        let control=model.control
        let current=control.detail?.id==id && model.matches(control)
        let readScope=AppCopy.text("appointments")+": "+AppCopy.text("details")
        VStack {
            if !current {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
            else if model.detailLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.detailFailure {
                VStack { Text(AppCopy.error(failure)).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure))); Button(AppCopy.text("retry")) { Task {await model.retryDetail(expected:control)} }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
            } else if let detail = model.session.detail, detail.appointment.id == id {
                Form {
                    Text(detail.appointment.title ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("status"), value: AppointmentStatusText.label(detail.appointment.status, text: AppCopy.text))
                    LabeledContent(AppCopy.text("intervalStart"), value: AgendaEndpoint.format(detail.appointment.start_at, timezone: model.session.selection?.business.timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("intervalEnd"), value: AgendaEndpoint.format(detail.appointment.end_at, timezone: model.session.selection?.business.timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable"))
                    if let scope = model.session.selection {
                        LabeledContent(AppCopy.text("timeZone"), value: scope.business.timezone)
                        if let issue = AgendaDayDisplay(items: [detail.appointment], day: scope.day, responseDay: scope.day, timezone: scope.business.timezone).sourceRows.first?.issue { Label(AppCopy.text(issue.rawValue), systemImage: "exclamationmark.triangle") }
                    }
                    LabeledContent(AppCopy.text("service"), value: detail.details.service?.name ?? AppCopy.text("notAvailable"))
                    LabeledContent(AppCopy.text("resource"), value: detail.details.resource?.id == nil ? AppCopy.text("notAvailable") : detail.details.resource?.name ?? AppCopy.text("notAvailable"))
                    if let notes = detail.details.notes, !notes.isEmpty { Section(AppCopy.text("notes")) { Text(notes) } }
                    if let booking=model.booking {AppointmentBookingSection(agenda:model,model:booking)}
                    if let lifecycle=model.lifecycle,let entry=model.lifecycleEntryControl {AppointmentLifecycleContent(model:lifecycle,isCurrent:{model.matchesLifecycleEntry(entry)},prepare:{action,child in model.prepareLifecycle(action,entry:entry,child:child)})}
                    if model.booking?.presented != true,let links = model.relations, let request = links.request {
                        AppointmentRelationLinks(links:links,isCurrent:{model.matches(control) && links.request==control.detail},onRetryParent: { Task {guard model.session.detailSelection==request else {return};await model.retryDetail(expected:control)} })
                    }
                }
            }
        }.navigationTitle(AppCopy.text("details"))
    }
}
