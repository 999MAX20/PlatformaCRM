import SwiftUI
import CRMCore

// Independently returned read projections. No action-key execution controls.
struct AttentionTargetContent: View {
    let detail: AttentionDetail
    let timezone: String?
    private func value(_ raw: String?) -> String { guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return AppCopy.text("notAvailable") }; return raw }
    private func date(_ raw: String?) -> String { raw.flatMap { AppointmentDate.format(startAt: $0, timezone: timezone, language: AppCopy.language) } ?? AppCopy.text("notAvailable") }
    private func status(_ raw: String) -> String {
        switch raw { case "open": AppCopy.text("taskOpen"); case "in_progress": AppCopy.text("taskInProgress"); case "done": AppCopy.text("taskDone"); case "cancelled": AppCopy.text("taskCancelled"); default: raw }
    }
    private func priority(_ raw: String?) -> String {
        switch raw { case "low": AppCopy.text("priorityLow"); case "normal": AppCopy.text("priorityNormal"); case "high": AppCopy.text("priorityHigh"); case "urgent": AppCopy.text("priorityUrgent"); default: value(raw) }
    }
    private func sender(_ raw: String?) -> String {
        switch raw { case "client": AppCopy.text("senderClient"); case "manager": AppCopy.text("senderManager"); case "ai": AppCopy.text("senderAi"); default: value(raw) }
    }
    var body: some View {
        Form {
            Label(AppCopy.text("fixtureMode"), systemImage: "testtube.2").font(.caption)
            Text(AppCopy.text("readOnly")).font(.caption)
            switch detail {
            case .task(let d):
                LabeledContent(AppCopy.text("taskTitle"), value: value(d.task.title))
                LabeledContent(AppCopy.text("status"), value: status(d.task.status))
                LabeledContent(AppCopy.text("taskPriority"), value: priority(d.task.priority))
                LabeledContent(AppCopy.text("taskDue"), value: date(d.task.due_at))
                Section(AppCopy.text("taskDescription")) { Text(value(d.details.description)) }
                Section(AppCopy.text("taskComments")) {
                    if d.commentsCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                    if d.comments.isEmpty { Text(AppCopy.text("taskNoComments")) }
                    ForEach(d.comments) { comment in VStack(alignment: .leading) { Text(value(comment.text)); Text(date(comment.created_at)).font(.caption) }.accessibilityElement(children: .combine) }
                }
            case .conversation(let d):
                Text(value(d.conversation.title)).font(.headline)
                LabeledContent(AppCopy.text("channel"), value: ReadChannelText.label(d.conversation.channel,text: AppCopy.text))
                LabeledContent(AppCopy.text("unread"), value: String(d.conversation.unread_count))
                if d.windowCapped { Label(AppCopy.text("partial"), systemImage: "exclamationmark.triangle") }
                if d.messages.isEmpty { Text(AppCopy.text("messagesEmpty")) }
                ForEach(d.messages) { message in
                    VStack(alignment: .leading) { Text(sender(message.sender_type)).font(.caption); Text(value(message.text)); Text(date(message.created_at)).font(.caption) }.accessibilityElement(children: .combine)
                }
            case .appointment(let d):
                Text(value(d.appointment.title)).font(.headline)
                LabeledContent(AppCopy.text("status"), value: AppointmentStatusText.label(d.appointment.status, text: AppCopy.text))
                LabeledContent(AppCopy.text("date"), value: date(d.appointment.start_at))
                LabeledContent(AppCopy.text("service"), value: value(d.details.service?.name))
                LabeledContent(AppCopy.text("resource"), value: d.details.resource?.id == nil ? AppCopy.text("notAvailable") : value(d.details.resource?.name))
                Section(AppCopy.text("notes")) { Text(value(d.details.notes)) }
            }
        }
    }
}
