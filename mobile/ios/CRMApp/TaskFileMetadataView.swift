import SwiftUI
import CRMCore

struct TaskFileMetadataControl:Equatable {let context:TaskFileMetadataContext;let visit:Int;let selected:TaskFileMetadata?}
@MainActor final class TaskFileMetadataViewModel:ObservableObject {
    @Published private(set) var context:TaskFileMetadataContext?
    @Published private(set) var items:[TaskFileMetadata]=[]
    @Published private(set) var selected:TaskFileMetadata?
    @Published private(set) var loading=false
    @Published private(set) var loaded=false
    @Published private(set) var failed=false
    @Published private var visit=0
    private var generation=0
    private let port:any TaskFileMetadataPort
    init(port:any TaskFileMetadataPort) {self.port=port}
    var control:TaskFileMetadataControl? {context.map {TaskFileMetadataControl(context:$0,visit:visit,selected:selected)}}
    func bind(_ next:TaskFileMetadataContext?) {let next=next?.valid==true ? next:nil;guard context != next else {return};context=next;generation += 1;visit += 1;items=[];selected=nil;loading=false;loaded=false;failed=false}
    func load(expected:TaskFileMetadataControl?) async {
        guard !Task.isCancelled,let expected,control==expected,selected==nil,!loading else {return}
        generation += 1;let ticket=generation;visit += 1;items=[];selected=nil;loading=true;loaded=false;failed=false
        do {let body=try await port.read(expected.context);guard !Task.isCancelled else {throw CancellationError()};let rows=try TaskFileMetadata.window(body,context:expected.context)
            guard generation==ticket,context==expected.context else {return};items=rows;loaded=true;loading=false;visit += 1
        } catch {guard generation==ticket,context==expected.context else {return};items=[];selected=nil;loading=false;loaded=false;failed=true;visit += 1}
    }
    func select(_ row:TaskFileMetadata,expected:TaskFileMetadataControl?) {guard let expected,control==expected,loaded,!loading,!failed,selected==nil,items.contains(row) else {return};selected=row;visit += 1}
    func back(expected:TaskFileMetadataControl?) {guard let expected,control==expected,selected != nil else {return};selected=nil;visit += 1}
}
struct TaskFileMetadataView:View {
    @ObservedObject var model:TaskFileMetadataViewModel
    let isCurrent:@MainActor ()->Bool
    var body:some View {
        let fileScope=AppCopy.text("taskFileMetadata"),detailScope=AppCopy.text("taskFileMetadata")+": "+AppCopy.text("details")
        if isCurrent(),let control=model.control {
            Section(AppCopy.text("taskFileMetadata")) {
                Text(AppCopy.text("fixtureMode")).font(.caption)
                Text(AppCopy.text("fileMetadataWindow")).font(.caption)
                Text(AppCopy.text("fileVerificationUnknown"))
                if model.loading {ProgressView(AppCopy.text("loading")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("loading")))}
                else if let row=model.selected {
                    LabeledContent(AppCopy.text("fileOriginalName"),value:row.original_name)
                    LabeledContent(AppCopy.text("fileContentType"),value:row.content_type.isEmpty ? AppCopy.text("notAvailable"):row.content_type)
                    LabeledContent(AppCopy.text("fileSizeBytes"),value:String(row.size))
                    LabeledContent(AppCopy.text("fileCreatedAt"),value:row.created_at)
                    Button(AppCopy.text("back")) {if isCurrent() {model.back(expected:control)}}.accessibilityLabel(Text(detailScope+": "+AppCopy.text("back")))
                } else {
                    if model.failed {Text(AppCopy.text("fileMetadataReadFailed")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("fileMetadataReadFailed"))).accessibilityAddTraits(.updatesFrequently)}
                    if model.loaded && model.items.isEmpty {Text(AppCopy.text("fileMetadataEmpty")).accessibilityLabel(Text(fileScope+": "+AppCopy.text("fileMetadataEmpty")))}
                    ForEach(model.items) {row in Button(row.original_name) {if isCurrent() {model.select(row,expected:control)}}}
                    Button(AppCopy.text("fileMetadataLoad")) {Task {if isCurrent() {await model.load(expected:control)}}}.accessibilityLabel(Text(fileScope+": "+AppCopy.text("fileMetadataLoad")))
                }
            }
        }
    }
}
