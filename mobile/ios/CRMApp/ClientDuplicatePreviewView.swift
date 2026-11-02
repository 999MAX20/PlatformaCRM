import SwiftUI
import CRMCore

struct ClientDuplicatePreviewSection: View {
    @ObservedObject var model: ClientDuplicatePreviewViewModel
    let load: @MainActor (ClientDuplicatePreviewVisit) async -> Void
    let isCurrent: @MainActor () -> Bool
    private func label(_ field: String) -> String {
        switch field {case "phone":AppCopy.text("clientPhone");case "email":AppCopy.text("clientEmail");case "whatsapp_id":"WhatsApp";case "telegram_id":"Telegram";case "instagram_id":"Instagram";default:AppCopy.text("notAvailable")}
    }
    var body: some View {
        let visit=model.visit;let readScope=AppCopy.text("clientDuplicatePreview")
        Section(AppCopy.text("clientDuplicatePreview")) {
            Text(AppCopy.text("clientDuplicateFixtureOnly")).font(.caption)
            if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
            else {
                if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently).accessibilityLabel(Text(readScope+": "+AppCopy.error(failure)))}
                if let result=model.result {
                    if result.duplicates.isEmpty {Text(AppCopy.text("clientDuplicateEmptyFixture")).accessibilityLabel(Text(readScope+": "+AppCopy.text("clientDuplicateEmptyFixture")))}
                    ForEach(result.duplicates,id:\.id) {row in
                        VStack(alignment:.leading) {
                            Text(row.full_name)
                            LabeledContent(AppCopy.text("clientPhone"),value:row.phone.isEmpty ? AppCopy.text("notAvailable") : row.phone)
                            LabeledContent(AppCopy.text("clientEmail"),value:row.email.isEmpty ? AppCopy.text("notAvailable") : row.email)
                            LabeledContent(AppCopy.text("clientDuplicateMatches"),value:row.matched_fields.map(label).joined(separator:", "))
                        }
                    }
                }
                Button(AppCopy.text(model.failure == nil ? "clientDuplicatePreview":"retry")) {Task {if isCurrent() {await load(visit)}}}.accessibilityLabel(Text(model.failure == nil ? readScope : readScope+": "+AppCopy.text("retry")))
            }
        }
    }
}
