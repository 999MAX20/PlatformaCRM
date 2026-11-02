import SwiftUI
import CRMCore

// Local result visit; never a server revision or command attempt.
struct ClientDuplicatePreviewVisit: Equatable {let generation: Int}
@MainActor final class ClientDuplicatePreviewViewModel: ObservableObject {
    @Published private(set) var result: ClientDuplicateResponse?
    @Published private(set) var loading=false
    @Published private(set) var failure: ReadFailure?
    @Published private var generation=0
    var visit: ClientDuplicatePreviewVisit {ClientDuplicatePreviewVisit(generation:generation)}
    private let source: any SyntheticClientDuplicatePreviewSource
    init(source: any SyntheticClientDuplicatePreviewSource) {self.source=source}
    func clear() {generation += 1;result=nil;loading=false;failure=nil}
    func load(_ input: ClientDuplicatePreviewInput,expected: ClientDuplicatePreviewVisit) async {
        guard visit == expected,!loading,input.context.valid else {return}
        clear();let ticket=generation;loading=true
        do {
            let value=try await source.preview(for:input)
            guard ticket == generation else {return}
            guard !Task.isCancelled,let value else {throw ReadFailure.unavailable}
            guard value.valid else {throw ReadFailure.invalidPayload}
            result=value;loading=false
        } catch {
            guard ticket == generation else {return};loading=false
            if !(error is CancellationError) {failure=error as? ReadFailure ?? .unavailable}
        }
    }
}
