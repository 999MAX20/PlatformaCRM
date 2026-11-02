import SwiftUI
import CRMCore

struct NotificationCenterScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: NotificationCenterViewModel
    private var business: Int? { agenda.session.selection?.business.id }
    private var current: Bool { model.business == business && model.scopeEpoch==agenda.businessEpoch }
    private func owns(_ expected:NotificationControl?) -> Bool {guard let expected else {return false};return model.matches(expected) && agenda.session.selection?.business.id==expected.business && agenda.businessEpoch==expected.epoch}
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private func category(_ raw: String?) -> String {
        switch raw { case nil: AppCopy.text("all"); case "sales": AppCopy.text("categorySales"); case "finance": AppCopy.text("categoryFinance"); case "system": AppCopy.text("categorySystem"); case "ai_alerts": AppCopy.text("categoryAi"); case "outreach": AppCopy.text("categoryOutreach"); case "tasks": AppCopy.text("categoryTasks"); default: value(raw) }
    }
    private func marker(_ item: CRMNotification) -> String { AppCopy.text(!item.readMarkerPresent ? "notAvailable" : item.unread ? "unread" : "notificationRead") }
    private func error(_ failure: ReadFailure) -> String { failure == .notFound ? AppCopy.text("notAvailable") : AppCopy.error(failure) }
    private func date(_ raw: String?) -> String { AppointmentDate.format(startAt: raw, timezone: agenda.session.selection?.business.timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable") }
    var body: some View {
        let control=model.control,epoch=agenda.businessEpoch,previousCategory=model.category,previousUnread=model.unreadOnly
        let readScope=AppCopy.text("notifications"),bootstrapScope=AppCopy.text("notifications")+": "+AppCopy.text("business")
        return NavigationStack {
            VStack(spacing: 12) {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business }, set: { id in Task { await agenda.load(business: id) } })) { ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) } }
                }
                if business == nil, let failure = agenda.failure {
                    Text(error(failure)).accessibilityLabel(Text(bootstrapScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else if business == nil || !current || model.loading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading"))) }
                else {
                    TextField(AppCopy.text("inboxSearch"), text: Binding(get:{model.query},set:{if owns(control) {model.search($0,expected:control)}})).textFieldStyle(.roundedBorder)
                    Toggle(AppCopy.text("unread"), isOn: Binding(get:{model.unreadOnly},set:{if owns(control) {model.filterUnread($0,previous:previousUnread,expected:control)}}))
                    Picker(AppCopy.text("notifications"), selection: Binding(get:{model.category},set:{if owns(control) {model.filterCategory($0,previous:previousCategory,expected:control)}})) {
                        Text(AppCopy.text("all")).tag(nil as String?)
                        ForEach(model.categories, id: \.self) { option in Text(category(option)).tag(Optional(option)) }
                    }
                    if let failure = model.failure { Text(error(failure)).accessibilityLabel(Text(readScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { if owns(control) {await model.retryList(expected:control)} } }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
                    else {
                        if model.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                        if model.showsEmpty { Text(AppCopy.text(model.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && model.category == nil && !model.unreadOnly ? "notificationsEmpty" : "noResults")) }
                        if model.visible.isEmpty { Button(AppCopy.text("retry")) { Task { if owns(control) {await model.retryList(expected:control)} } }.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry"))) }
                        List(model.visible) { item in
                            Button { if owns(control) {model.open(id:item.id,expected:control)} } label: {
                                VStack(alignment: .leading, spacing: 4) { Text(value(item.text)); Text("\(category(item.category)) · \(marker(item))").font(.caption) }.foregroundStyle(.primary)
                            }
                        }.listStyle(.plain)
                    }
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal).navigationTitle(AppCopy.text("notifications"))
            .environment(\.locale, Locale(identifier: AppCopy.language))
            .navigationDestination(isPresented: Binding(get: { current && model.selected != nil }, set: { if !$0,owns(control) {model.close(expected:control)} })) { if current { cardContent } }
            .task(id: "\(business ?? 0):\(epoch)") {guard agenda.session.selection?.business.id==business,agenda.businessEpoch==epoch else {return};if !current || (!model.loaded && !model.loading && model.failure==nil) {await model.load(business:business,epoch:epoch)}}
        }
    }
    private var cardContent: some View {
        let control=model.control
        return Form {
            Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
            if let item = model.selected {
                Text(value(item.text)); Text(category(item.category)); Text(marker(item))
                LabeledContent(AppCopy.text("status"), value: NotificationStatusText.label(item.status,text: AppCopy.text))
                LabeledContent(AppCopy.text("channel"), value: ReadChannelText.label(item.channel,text: AppCopy.text))
                #if DEBUG
                if model.routeEditorActive { routeContent }
                else { Button(AppCopy.text("relativeRouteCheck")) {if owns(control) {model.beginRoute(expected:control)}} }
                #endif
                if !model.routeEditorActive {
                    NotificationMarkReadView(model:model.markRead,isCurrent:{owns(control)})
                    NotificationMarkUnreadView(model:model.markUnread,isCurrent:{owns(control)})
                    if item.appointmentTarget != nil { Button("\(AppCopy.text("openTarget")) · \(AppCopy.text("appointments"))") { Task { if owns(control) {await model.openTarget(expected:control)} } } }
                }
            }
        }.navigationTitle(AppCopy.text("notifications"))
        .navigationDestination(isPresented: Binding(get: { current && model.targetActive }, set: { if !$0,owns(control) {model.backTarget(expected:control)} })) { if current { targetContent } }
    }
    #if DEBUG
    private var routeContent: some View {
        let captured=model.routeControl
        return Section(AppCopy.text("relativeRouteCheck")) {
            if model.routeReviewing {
                Text(model.routeInput).textSelection(.enabled)
                Text(AppCopy.text(model.routeCandidate == nil ? "relativeRouteUnsupported" : model.routeCorroborated ? "relativeRouteMatched" : "relativeRouteUntrusted"))
            } else {
                TextField(AppCopy.text("relativeRouteInput"),text:Binding(get:{model.routeInput},set:{if owns(captured?.parent) {model.editRoute($0,expected:captured)}}))
                Button(AppCopy.text("relativeRouteReview")) {if owns(captured?.parent) {model.reviewRoute(expected:captured)}}
            }
            Button(AppCopy.text("back")) {if owns(captured?.parent) {model.backRoute(expected:captured)}}.accessibilityLabel(Text(AppCopy.text("notifications")+": "+AppCopy.text("back")))
        }
    }
    #endif
    private var targetContent: some View {
        let control=model.control
        let targetScope=AppCopy.text("notifications")+": "+AppCopy.text("appointments")+": "+AppCopy.text("details")
        return Group {
            if model.targetLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(targetScope+": "+AppCopy.text("loading"))) }
            else if let failure = model.targetFailure { VStack { Text(error(failure)).accessibilityLabel(Text(targetScope+": "+error(failure))); Button(AppCopy.text("retry")) { Task { if owns(control) {await model.openTarget(expected:control)} } }.accessibilityLabel(Text(targetScope+": "+AppCopy.text("retry"))) } }
            else if let detail = model.target {
                Form {
                    Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                    Text(value(detail.appointment.title))
                    LabeledContent(AppCopy.text("status"), value: AppointmentStatusText.label(detail.appointment.status, text: AppCopy.text))
                    LabeledContent(AppCopy.text("date"), value: date(detail.appointment.start_at))
                    LabeledContent(AppCopy.text("service"), value: value(detail.details.service?.name))
                    LabeledContent(AppCopy.text("resource"), value: detail.details.resource?.id == nil ? AppCopy.text("notAvailable") : value(detail.details.resource?.name))
                    if let notes = detail.details.notes, !notes.isEmpty { Section(AppCopy.text("notes")) { Text(notes) } }
                }
            }
        }.navigationTitle(AppCopy.text("appointments"))
    }
}
