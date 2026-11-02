import Foundation
import SwiftUI
import CRMCore

@MainActor final class InboxTaskSourceViewModel:ObservableObject {
    @Published private(set) var session=InboxTaskSourceSession()
    private let repository:any InboxTaskSourceRepository
    var controlsBlocked:@MainActor ()->Bool={false}
    init(repository:any InboxTaskSourceRepository) {self.repository=repository}
    var control:InboxTaskSourceControl? {session.control}
    func bind(_ context:InboxConversationFilesContext?) {session.bind(context)}
    func show() {session.show()}
    func hide() {session.hide()}
    func use(expected:InboxTaskSourceControl?) {if !controlsBlocked() {session.use(expected:expected)}}
    func clearChoice(expected:InboxTaskSourceControl?) {if !controlsBlocked() {session.clearChoice(expected:expected)}}
    func read(expected:InboxTaskSourceControl?) async {
        guard !controlsBlocked(),!Task.isCancelled,let ticket=session.begin(expected:expected) else {return}
        do {let source=try await repository.source(ticket.context);try Task.checkCancellation();session.accept(source,ticket:ticket)}
        catch {if error is CancellationError {session.cancel(ticket:ticket)} else {session.fail(error as? ReadFailure ?? .unavailable,ticket:ticket)}}
    }
}
