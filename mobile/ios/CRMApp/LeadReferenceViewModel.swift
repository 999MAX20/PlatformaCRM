import Foundation
import SwiftUI
import CRMCore

@MainActor final class LeadReferenceViewModel:ObservableObject {
    @Published private(set) var session=LeadReadSession()
    private let repository:any LeadReadRepository
    init(repository:any LeadReadRepository) {self.repository=repository}
    var controlsBlocked:@MainActor ()->Bool={false}
    var control:LeadReadControl? {session.control}
    func bind(_ context:InboxConversationFilesContext?) {session.bind(context)}
    func show() {session.show()}
    func hide() {session.hide()}
    func update(_ raw:String,input:LeadReadInput?) {if !controlsBlocked() {session.update(raw,input:input)}}
    func clear(expected:LeadReadControl?) {if !controlsBlocked() {session.clear(expected:expected)}}
    func back(expected:LeadReadControl?) {if !controlsBlocked() {session.backProfile(expected:expected)}}
    func use(expected:LeadReadControl?) {if !controlsBlocked() {session.use(expected:expected)}}
    func clearChoice(expected:LeadReadControl?) {if !controlsBlocked() {session.clearChoice(expected:expected)}}
    func search(expected:LeadReadControl?) async {
        guard !controlsBlocked(),!Task.isCancelled,let ticket=session.beginList(expected:expected) else {return}
        do {let page=try await repository.leads(business:ticket.context.business,search:ticket.query);try Task.checkCancellation();session.accept(page,ticket:ticket)}
        catch {if error is CancellationError {session.cancel(ticket:ticket)} else {session.fail(error as? ReadFailure ?? .unavailable,ticket:ticket)}}
    }
    func open(_ id:Int,expected:LeadReadControl?) async {
        guard !controlsBlocked(),!Task.isCancelled,let ticket=session.beginProfile(id:id,expected:expected) else {return}
        do {let profile=try await repository.lead(business:ticket.context.business,id:id);try Task.checkCancellation();session.accept(profile,ticket:ticket)}
        catch {if error is CancellationError {session.cancel(ticket:ticket)} else {session.fail(error as? ReadFailure ?? .unavailable,ticket:ticket)}}
    }
}
