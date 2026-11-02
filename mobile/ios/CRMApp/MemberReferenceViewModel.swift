import Foundation
import SwiftUI
import CRMCore

@MainActor final class MemberReferenceViewModel:ObservableObject {
    @Published private(set) var session=MemberReferenceSession()
    private let repository:any TeamMemberReadRepository
    var controlsBlocked:@MainActor ()->Bool={false}
    init(repository:any TeamMemberReadRepository) {self.repository=repository}
    var control:MemberReferenceControl? {session.control}
    func bind(_ context:InboxConversationFilesContext?) {session.bind(context)}
    func show() {session.show()}
    func hide() {session.hide()}
    func update(_ raw:String,input:MemberReferenceInput?) {if !controlsBlocked() {session.update(raw,input:input)}}
    func clear(expected:MemberReferenceControl?) {if !controlsBlocked() {session.clear(expected:expected)}}
    func use(expected:MemberReferenceControl?) {if !controlsBlocked() {session.use(expected:expected)}}
    func clearChoice(expected:MemberReferenceControl?) {if !controlsBlocked() {session.clearChoice(expected:expected)}}
    func read(expected:MemberReferenceControl?) async {
        guard !controlsBlocked(),!Task.isCancelled,let ticket=session.begin(expected:expected) else {return}
        do {let source=try await repository.member(business:ticket.context.business,id:ticket.id);try Task.checkCancellation();session.accept(source,ticket:ticket)}
        catch {if error is CancellationError {session.cancel(ticket:ticket)} else {session.fail(error as? ReadFailure ?? .unavailable,ticket:ticket)}}
    }
}
