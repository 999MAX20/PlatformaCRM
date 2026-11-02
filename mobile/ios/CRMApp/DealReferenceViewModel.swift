import Foundation
import SwiftUI
import CRMCore

@MainActor final class DealReferenceViewModel:ObservableObject {
    @Published private(set) var session=DealReferenceSession()
    private let repository:any DealReadRepository
    var controlsBlocked:@MainActor ()->Bool={false}
    init(repository:any DealReadRepository) {self.repository=repository}
    var control:DealReferenceControl? {session.control}
    func bind(_ context:InboxConversationFilesContext?) {session.bind(context)}
    func show() {session.show()}
    func hide() {session.hide()}
    func update(_ raw:String,input:DealReferenceInput?) {if !controlsBlocked() {session.update(raw,input:input)}}
    func clear(expected:DealReferenceControl?) {if !controlsBlocked() {session.clear(expected:expected)}}
    func use(expected:DealReferenceControl?) {if !controlsBlocked() {session.use(expected:expected)}}
    func clearChoice(expected:DealReferenceControl?) {if !controlsBlocked() {session.clearChoice(expected:expected)}}
    func read(expected:DealReferenceControl?) async {
        guard !controlsBlocked(),!Task.isCancelled,let ticket=session.begin(expected:expected) else {return}
        do {let source=try await repository.deal(business:ticket.context.business,id:ticket.id);try Task.checkCancellation();session.accept(source,ticket:ticket)}
        catch {if error is CancellationError {session.cancel(ticket:ticket)} else {session.fail(error as? ReadFailure ?? .unavailable,ticket:ticket)}}
    }
}
