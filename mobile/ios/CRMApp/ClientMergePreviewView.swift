import SwiftUI
import CRMCore

struct ClientMergePreviewSection: View {
    @ObservedObject var owner: ClientProfileViewModel
    @ObservedObject var model: ClientMergePreviewViewModel
    let isCurrent: @MainActor () -> Bool
    private let countKeys=[
        "leads":"clientMergeCountLeads",
        "appointments":"clientMergeCountAppointments",
        "conversations":"clientMergeCountConversations",
        "bot_conversations":"clientMergeCountBotConversations",
        "tasks":"clientMergeCountTasks",
        "deals":"clientMergeCountDeals",
        "notes":"clientMergeCountNotes",
        "activity_events":"clientMergeCountActivityEvents",
        "analytics_events":"clientMergeCountAnalyticsEvents",
        "notifications":"clientMergeCountNotifications",
        "tags":"clientMergeCountTags",
        "attachments":"clientMergeCountAttachments",
        "custom_field_values":"clientMergeCountCustomFieldValues"
    ]
    var body: some View {
        let entry=owner.mergeEntry,control=model.control;let readScope=AppCopy.text("clientMergePreviewTitle")
        Section(AppCopy.text("clientMergePreviewTitle")) {
            Text(AppCopy.text("clientMergeFixtureOnly")).font(.caption)
            if let control,owner.ownsMerge(control) {
                Button(AppCopy.text("back")) {if isCurrent() {_=owner.closeMerge(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                if !model.catalogReady {
                    if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let failure=model.failure {
                        Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)))
                        Button(AppCopy.text("retry")) {Task {if isCurrent() {await owner.retryMerge(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))
                    }
                } else {
                    Text(AppCopy.text("clientMergeChoose"))
                    if model.candidates.isEmpty {Text(AppCopy.text("clientMergeEmpty")).accessibilityLabel(Text(readScope+": "+AppCopy.text("clientMergeEmpty")))}
                    ForEach(model.candidates,id:\.id) {row in
                        Button {if isCurrent() {owner.chooseMerge(row.id,expected:control)}} label: {
                            VStack(alignment:.leading) {
                                HStack {Text(row.full_name);if model.selected == row.id {Image(systemName:"checkmark")}}
                                Text(row.phone);Text(row.email)
                            }
                        }.accessibilityAddTraits(model.selected == row.id ? .isSelected:[])
                    }
                    if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else {
                        if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)))}
                        if model.selected != nil {Button(AppCopy.text(model.failure == nil ? "clientDraftReview":"retry")) {Task {if isCurrent() {await owner.previewMerge(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text(model.failure == nil ? "clientDraftReview":"retry")))}
                        if let preview=model.result {
                            Text(preview.duplicate.full_name).font(.headline)
                            Text(AppCopy.text("clientMergeArchivePolicy"))
                            ForEach(ClientMergeTransferCounts.fields,id:\.self) {field in
                                if let key=countKeys[field],let value=preview.transferred.provided[field] {LabeledContent(AppCopy.text(key),value:String(value))}
                            }
                        }
                    }
                }
            } else if let entry {Button(AppCopy.text("clientMergePreviewTitle")) {Task {if isCurrent() {await owner.openMerge(expected:entry)}}}}
        }
    }
}
