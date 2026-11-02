import SwiftUI
import CRMCore

struct InboxLinkClientContent:View {
    @ObservedObject var model:InboxLinkClientViewModel
    let isCurrent:@MainActor ()->Bool
    private func label(_ c:TaskDraftClientChoice)->String {(c.title.flatMap {$0.isEmpty ? nil:$0} ?? AppCopy.text("notAvailable"))+" · #\(c.id)"}
    var body:some View {
        let control=model.control
        if isCurrent(),model.presented {
            Section(AppCopy.text("inboxLinkTitle")) {
                Text(AppCopy.text("inboxLinkBoundary")).font(.caption)
                if model.loading {ProgressView(AppCopy.text("loading"))}
                if let failure=model.failure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently)}
                if let record=model.record {
                    Text(AppCopy.text(record.phase == .pending ? "inboxLinkPending":record.phase == .response ? "inboxLinkResponse":record.phase == .rejected ? "inboxLinkRejected":"inboxLinkUnknown")).accessibilityAddTraits(.updatesFrequently)
                    LabeledContent(AppCopy.text("inboxLinkOriginal"),value:record.attempt.review.source.client.map {"#\($0)"} ?? AppCopy.text("inboxLinkNotLinked"))
                    LabeledContent(AppCopy.text("inboxLinkCandidate"),value:label(record.attempt.review.candidate.choice))
                    Text(record.attempt.review.candidate.rawQuery)
                    if record.phase == .response || record.phase == .rejected {Button(AppCopy.text("inboxLinkAcknowledge")) {if isCurrent() {model.acknowledge(record,expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLinkTitle")+": "+AppCopy.text("inboxLinkAcknowledge")))}
                } else if model.blocked {Text(AppCopy.text("inboxLinkRetained"))}
                else if let review=model.review {
                    LabeledContent(AppCopy.text("inboxLinkOriginal"),value:review.source.client.map {"#\($0)"} ?? AppCopy.text("inboxLinkNotLinked"))
                    LabeledContent(AppCopy.text("inboxLinkCandidate"),value:label(review.candidate.choice));Text(review.candidate.rawQuery)
                    Button(AppCopy.text("inboxLinkSubmit")) {Task {if isCurrent() {await model.submit(expected:control)}}}.disabled(!model.canSubmit)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLinkTitle")+": "+AppCopy.text("back")))
                } else if model.editing {
                    if let picker=model.picker {InboxLinkClientPickerContent(model:model,picker:picker,isCurrent:isCurrent)}
                    if let candidate=model.candidate {Text(label(candidate.choice));Button(AppCopy.text("inboxLinkClear")) {if isCurrent() {model.clearChoice(expected:control)}}}
                    Button(AppCopy.text("inboxLinkReview")) {if isCurrent() {model.prepare(expected:control)}}.disabled(!model.canPrepare)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(AppCopy.text("inboxLinkTitle")+": "+AppCopy.text("back")))
                } else {
                    if let source=model.source {LabeledContent(AppCopy.text("inboxLinkOriginal"),value:source.client.map {"#\($0)"} ?? AppCopy.text("inboxLinkNotLinked"))}
                    if model.canOpen {Button(AppCopy.text("inboxLinkChoose")) {if isCurrent() {model.open(expected:control)}}}
                }
                if model.canLoad {Button(AppCopy.text("inboxLinkLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}}
            }
        }
    }
}
private struct InboxLinkClientPickerContent:View {
    @ObservedObject var model:InboxLinkClientViewModel
    @ObservedObject var picker:ClientSearchViewModel
    @ObservedObject var profile:ClientProfileViewModel
    let isCurrent:@MainActor ()->Bool
    init(model:InboxLinkClientViewModel,picker:ClientSearchViewModel,isCurrent:@escaping @MainActor ()->Bool) {self.model=model;self.picker=picker;self.profile=picker.profile;self.isCurrent=isCurrent}
    var body:some View {
        let parent=model.control,child=picker.control,input=model.input
        if isCurrent(),model.canEdit {
            if let selected=picker.session.profileSelection {
                if profile.loading {ProgressView(AppCopy.text("loading"))}
                else if let failure=profile.failure {Text(AppCopy.error(failure));Button(AppCopy.text("retry")) {Task {if isCurrent() {await model.retryClient(expected:parent,child:child)}}}}
                else if let detail=profile.detail,detail.valid(for:selected.selection.context.business,id:selected.id) {Text((detail.client.title ?? AppCopy.text("notAvailable"))+" · #\(detail.client.id)");Button(AppCopy.text("inboxLinkUse")) {if isCurrent() {model.useClient(expected:parent,child:child)}}}
                Button(AppCopy.text("back")) {if isCurrent() {model.backClient(expected:parent,child:child)}}.accessibilityLabel(Text(AppCopy.text("inboxLinkTitle")+": "+AppCopy.text("details")+": "+AppCopy.text("back")))
            } else {
                TextField(AppCopy.text("clientSearch"),text:Binding(get:{picker.session.query},set:{if isCurrent() {model.update($0,input:input)}})).disabled(picker.session.loading)
                Button(AppCopy.text("searchSubmit")) {Task {if isCurrent() {await model.search(expected:parent,child:child)}}}.disabled(picker.session.loading)
                if picker.session.loading {ProgressView(AppCopy.text("loading"))}
                else if let failure=picker.session.failure {Text(AppCopy.error(failure)).accessibilityAddTraits(.updatesFrequently)}
                else if picker.session.loaded {
                    Text(AppCopy.text("clientSearchCount").replacingOccurrences(of:"{loaded}",with:String(picker.session.items.count)).replacingOccurrences(of:"{total}",with:String(picker.session.total))).font(.caption)
                    if picker.session.partial {Text(AppCopy.text("partial"))};if picker.session.showsEmpty {Text(AppCopy.text("noResults"))}
                    ForEach(picker.session.items) {row in Button((row.title ?? AppCopy.text("notAvailable"))+" · #\(row.id)") {Task {if isCurrent() {await model.openClient(row.id,expected:parent,child:child)}}}}
                }
            }
        }
    }
}
