import SwiftUI
import CRMCore

struct HomeTodayScreen: View {
    @ObservedObject var agenda: AgendaViewModel
    @ObservedObject var model: HomeTodayViewModel
    private var business: Business? { agenda.session.selection?.business }
    private func owns(_ owner:HomeOwnerControl?)->Bool {guard let owner else {return false};return model.owner==owner && agenda.session.selection?.business.id==owner.business && agenda.businessEpoch==owner.epoch}
    private func value(_ raw: String?) -> String { guard let raw, !raw.isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private func count(_ n: Int?) -> String { n.map(String.init) ?? AppCopy.text("notAvailable") }
    var body: some View {
        let epoch=agenda.businessEpoch
        let homeControl=model.homeControl,todayControl=model.todayControl,navigation=model.navigationControl
        let homeScope=AppCopy.text("home"),bootstrapScope=AppCopy.text("home")+": "+AppCopy.text("business"),todayScope=AppCopy.text("home")+": "+AppCopy.text("today")
        Form {
            Section {
                Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
                if let business {
                    Picker(AppCopy.text("business"), selection: Binding(get: { business.id }, set: {id in Task {if agenda.session.selection?.business.id==business.id && agenda.businessEpoch==epoch {await agenda.load(business:id)}}})) {
                        ForEach(agenda.session.businesses) { Text($0.name).tag($0.id) }
                    }
                } else if let failure = agenda.failure {
                    Text(AppCopy.error(failure)).accessibilityLabel(Text(bootstrapScope+": "+AppCopy.error(failure))); Button(AppCopy.text("retry")) { Task { await agenda.start() } }.accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("retry")))
                } else { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(bootstrapScope+": "+AppCopy.text("loading"))) }
            }
            if let business, model.business == business.id,model.scopeEpoch==agenda.businessEpoch {
                Section(AppCopy.text("home")) {
                    if model.homeLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(homeScope+": "+AppCopy.text("loading"))) }
                    else if let failure = model.homeFailure { Text(AppCopy.error(failure)).accessibilityLabel(Text(homeScope+": "+AppCopy.error(failure))) }
                    else if let home = model.home {
                        LabeledContent(AppCopy.text("todayAppointments"), value: count(home.sections.appointments?.today))
                        LabeledContent(AppCopy.text("openTasks"), value: count(home.sections.tasks?.open))
                        LabeledContent(AppCopy.text("inbox") + " · " + AppCopy.text("unread"), value: count(home.sections.conversations?.unread))
                    }
                    Button(AppCopy.text("retry")) { Task {if owns(homeControl?.owner) {await model.reloadHome(expected:homeControl)}} }.accessibilityLabel(Text(homeScope+": "+AppCopy.text("retry"))).disabled(model.homeLoading)
                }
                Section(AppCopy.text("today")) {
                    if let day = model.day { LabeledContent(AppCopy.text("date"), value: day) }
                    if model.todayLoading { ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(todayScope+": "+AppCopy.text("loading"))) }
                    else if let failure = model.todayFailure { Text(AppCopy.error(failure)).accessibilityLabel(Text(todayScope+": "+AppCopy.error(failure))) }
                    else if let today = model.today {
                        if let a = today.sections.appointments {
                            LabeledContent(AppCopy.text("appointments"), value: String(a.total))
                            if a.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                            if a.total == 0 { Text(AppCopy.text("todayAppointmentsEmpty")) }
                            ForEach(a.items) { item in
                                VStack(alignment: .leading) {
                                    Text(value(item.title)); Text(AppointmentDate.format(startAt: item.start_at, timezone: business.timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable")).font(.caption)
                                }.accessibilityElement(children: .combine)
                            }
                        } else { Text(AppCopy.text("appointments") + ": " + AppCopy.text("notAvailable")) }
                        if let t = today.sections.tasks {
                            LabeledContent(AppCopy.text("tasks"), value: String(t.total))
                            if t.partial { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                            if t.total == 0 { Text(AppCopy.text("todayTasksEmpty")) }
                            ForEach(t.items) { item in
                                VStack(alignment: .leading) {
                                    Text(value(item.title)); Text(item.due_at.flatMap { AppointmentDate.format(startAt: $0, timezone: business.timezone, language: AppCopy.language) } ?? AppCopy.text("notAvailable")).font(.caption)
                                }.accessibilityElement(children: .combine)
                            }
                        } else { Text(AppCopy.text("tasks") + ": " + AppCopy.text("notAvailable")) }
                    }
                    Button(AppCopy.text("retry")) { Task {if owns(todayControl?.owner) {await model.reloadToday(expected:todayControl)}} }.accessibilityLabel(Text(todayScope+": "+AppCopy.text("retry"))).disabled(model.todayLoading)
                }
                Section {
                    ForEach(HomeDestination.allCases, id: \.rawValue) { target in Button(AppCopy.text(target.rawValue)) {if owns(navigation?.owner) {model.open(target,expected:navigation)}} }
                }
            }
        }
        .environment(\.locale, Locale(identifier: AppCopy.language))
        .task(id: "\(business?.id ?? 0):\(epoch)") {
            if let business,agenda.session.selection?.business.id==business.id,agenda.businessEpoch==epoch {await model.start(business:business.id,day:model.currentDay(timezone:business.timezone),epoch:epoch)}
        }
    }
}
