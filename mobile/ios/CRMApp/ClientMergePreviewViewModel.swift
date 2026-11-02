import SwiftUI
import CRMCore

// Local catalog/selection/result visit, not a source entity version or command attempt.
struct ClientMergePreviewControl: Equatable {let context:ClientMergePreviewContext;let visit:Int;let duplicate:Int?}
@MainActor final class ClientMergePreviewViewModel: ObservableObject {
    @Published private(set) var context: ClientMergePreviewContext?
    @Published private(set) var candidates: [ClientMergeSnapshot]=[]
    @Published private(set) var selected: Int?
    @Published private(set) var result: ClientMergePreview?
    @Published private(set) var loading=false
    @Published private(set) var catalogReady=false
    @Published private(set) var failure: ReadFailure?
    @Published private var visit=0
    private let source: any SyntheticClientMergePreviewSource
    init(source: any SyntheticClientMergePreviewSource) {self.source=source}
    var control: ClientMergePreviewControl? {context.map {ClientMergePreviewControl(context:$0,visit:visit,duplicate:selected)}}
    func clear() {visit += 1;context=nil;candidates=[];selected=nil;result=nil;loading=false;catalogReady=false;failure=nil}
    func open(_ context: ClientMergePreviewContext) async {
        clear();guard context.valid else {return};self.context=context;let ticket=visit;loading=true
        do {
            let rows=try await source.candidates(for:context)
            guard ticket == visit else {return}
            guard !Task.isCancelled,let rows else {throw ReadFailure.unavailable}
            guard rows.allSatisfy({$0.id > 0 && $0.id != context.target}),Set(rows.map(\.id)).count == rows.count else {throw ReadFailure.invalidPayload}
            candidates=rows;catalogReady=true;loading=false
        } catch {guard ticket == visit else {return};loading=false;if !(error is CancellationError) {failure=error as? ReadFailure ?? .unavailable}}
    }
    func choose(_ id: Int,expected: ClientMergePreviewControl?) {
        guard let expected,control == expected,catalogReady,candidates.contains(where:{$0.id == id}) else {return}
        visit += 1;selected=id;result=nil;failure=nil;loading=false
    }
    func preview(expected: ClientMergePreviewControl?) async {
        guard let expected,control == expected,!loading,catalogReady,let id=selected,candidates.contains(where:{$0.id == id}) else {return}
        visit += 1;let ticket=visit;result=nil;failure=nil;loading=true
        do {
            let value=try await source.preview(for:expected.context,duplicate:id)
            guard ticket == visit else {return}
            guard !Task.isCancelled,let value else {throw ReadFailure.unavailable}
            guard value.matches(expected.context,duplicate:id),value.duplicate == candidates.first(where:{$0.id == id}) else {throw ReadFailure.invalidPayload}
            result=value;loading=false
        } catch {guard ticket == visit else {return};loading=false;if !(error is CancellationError) {failure=error as? ReadFailure ?? .unavailable}}
    }
}
