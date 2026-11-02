import SwiftUI
import CRMCore

struct AgendaDayContent: View {
    let display: AgendaDayDisplay
    let mode: AgendaMode
    let timezone: String
    let onOpen: (Int) -> Void
    var body: some View {
        List {
            if mode == .calendar {
                if !display.scheduled.isEmpty {
                    Section(AppCopy.text("dayAgenda")) { ForEach(display.scheduled) { row in link(row) } }
                }
                if !display.uncertain.isEmpty {
                    Section(AppCopy.text("attention")) { ForEach(display.uncertain) { row in link(row) } }
                }
            } else { ForEach(display.sourceRows) { row in link(row) } }
        }.listStyle(.plain)
    }
    private func link(_ row: AgendaDayRow) -> some View {
        Button { onOpen(row.id) } label: { AgendaDayRowContent(row: row, timezone: timezone, mode: mode).foregroundStyle(.primary) }
    }
}
private struct AgendaDayRowContent: View {
    let row: AgendaDayRow
    let timezone: String
    let mode: AgendaMode
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private var endpoints: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(AppCopy.text("intervalStart") + ": " + (AgendaEndpoint.format(row.appointment.start_at, timezone: timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable")))
            Text(AppCopy.text("intervalEnd") + ": " + (AgendaEndpoint.format(row.appointment.end_at, timezone: timezone, language: AppCopy.language) ?? AppCopy.text("notAvailable")))
        }.font(.caption)
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if mode == .calendar { endpoints }
            Text(value(row.appointment.title)).font(.headline)
            if mode == .list { endpoints }
            Text(AppCopy.text("status") + ": " + AppointmentStatusText.label(row.appointment.status, text: AppCopy.text)).font(.caption)
            Text(AppCopy.text("resource") + ": " + AppCopy.text("notAvailable")).font(.caption)
            if let issue = row.issue { Label(AppCopy.text(issue.rawValue), systemImage: "exclamationmark.triangle").font(.caption) }
        }.accessibilityElement(children: .combine)
    }
}
