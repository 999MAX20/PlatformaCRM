import SwiftUI
import CRMCore

struct LeadReferenceContent:View {
    @ObservedObject var model:LeadReferenceViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        let s=model.session,control=model.control,input=s.input
        let readScope=s.selectedID.map {AppCopy.text("leadReferenceTitle")+" #\($0)"} ?? AppCopy.text("leadReferenceSearch")
        if isCurrent(),s.presented {
            Section(AppCopy.text("leadReferenceTitle")) {
                Text(AppCopy.text("leadReferenceReadOnly")).font(.caption)
                if let choice=s.choice {LabeledContent(AppCopy.text("leadReferenceChosen"),value:choice.detail.lead.title+" · #\(choice.detail.lead.id)");Button(AppCopy.text("leadReferenceClearChoice")) {if isCurrent() {model.clearChoice(expected:control)}}}
                if s.selectedID != nil {
                    if s.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let error=s.failure {Text(AppCopy.error(error)).accessibilityLabel(Text(readScope+": "+AppCopy.error(error))).accessibilityAddTraits(.updatesFrequently);if let id=s.selectedID {Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.open(id,expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("retry")))}}
                    else if let detail=s.detail {
                        Text(detail.lead.title+" · #\(detail.lead.id)");LabeledContent(AppCopy.text("leadReferenceClient"),value:detail.lead.client.name+" · #\(detail.lead.client_id)");Text(detail.lead.status);Text(detail.lead.source);Text(detail.details.message)
                        Button(AppCopy.text("leadReferenceUse")) {if isCurrent() {model.use(expected:control)}}.disabled(!s.canUse)
                    }
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("back")))
                } else {
                    TextField(AppCopy.text("leadReferenceSearch"),text:Binding(get:{model.session.query},set:{if isCurrent() {model.update($0,input:input)}})).disabled(s.loading)
                    Button(AppCopy.text("searchSubmit")) {Task {if isCurrent() {await model.search(expected:control)}}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchSubmit"))).disabled(s.loading)
                    Button(AppCopy.text("searchClear")) {if isCurrent() {model.clear(expected:control)}}.accessibilityLabel(Text(readScope+": "+AppCopy.text("searchClear"))).disabled(s.loading)
                    if s.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(readScope+": "+AppCopy.text("loading")))}
                    else if let error=s.failure {Text(AppCopy.error(error)).accessibilityLabel(Text(readScope+": "+AppCopy.error(error))).accessibilityAddTraits(.updatesFrequently)}
                    else if s.loaded {
                        Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(s.items.count)).replacingOccurrences(of:"{total}",with:String(s.total)))
                        if s.partial {Text(AppCopy.text("partial"))};if s.showsEmpty {Text(AppCopy.text("noResults"))}
                        ForEach(s.items,id:\.id) {row in Button(row.title+" · #\(row.id)") {Task {if isCurrent() {await model.open(row.id,expected:control)}}}}
                    }
                }
            }.disabled(model.controlsBlocked())
        }
    }
}
