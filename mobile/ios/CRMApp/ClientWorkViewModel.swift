import Foundation
import SwiftUI
import CRMCore

// Local child presentation; no wire version, rights or durable recovery token.
struct ClientWorkControl:Equatable {let selection:ClientReadSelection;let generation:Int;let target:ClientWorkTarget?}

@MainActor final class ClientWorkViewModel: ObservableObject {
    @Published private(set) var selection: ClientReadSelection?
    @Published private(set) var parent: ClientProfile?
    @Published private(set) var tasks: [WorkTask]?
    @Published private(set) var conversations: [InboxConversation]?
    @Published private(set) var appointments: [Appointment]?
    @Published private(set) var selected: ClientWorkTarget?
    @Published private(set) var detail: AttentionDetail?
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    @Published private var revision = 0
    private let repository: any ClientWorkRepository
    init(repository: any ClientWorkRepository) { self.repository = repository }
    func bind(_ profile: ClientProfile, selection: ClientReadSelection) {
        clear()
        guard selection.revision > 0, profile.valid(for: selection.business, id: selection.id) else { return }
        self.selection = selection; parent = profile
        tasks = profile.providedTasks; conversations = profile.providedConversations
        appointments = profile.providedAppointments
    }
    func open(_ target: ClientWorkTarget, expected: ClientReadSelection? = nil) async {
        if let expected, expected != selection { return }
        guard let request = selection, contains(target) else { return }
        back(); selected = target; loading = true; let ticket = revision
        do {
            let result: AttentionDetail
            switch target {
            case .task(let id):
                let value = try await repository.taskDetails(business: request.business, id: id)
                guard value.valid(for: request.business, id: id), value.task.client_id == request.id else { throw ReadFailure.invalidPayload }
                result = .task(value)
            case .conversation(let id):
                let value = try await repository.thread(business: request.business, id: id)
                guard value.valid(for: request.business, id: id), value.clientReferenceID == request.id else { throw ReadFailure.invalidPayload }
                result = .conversation(value)
            case .appointment(let id):
                let value = try await repository.appointment(business: request.business, id: id)
                guard value.business == request.business, value.appointment.id == id, value.linkedClientID == request.id else { throw ReadFailure.invalidPayload }
                result = .appointment(value)
            }
            guard current(request, target, ticket) else { return }
            detail = result; loading = false
            switch result {
            case .task(let value): tasks = tasks?.map { $0.id == value.task.id ? value.task : $0 }
            case .conversation(let value): conversations = conversations?.map { $0.id == value.conversation.id ? value.conversation : $0 }
            case .appointment(let value): appointments = appointments?.map { $0.id == value.appointment.id ? value.appointment : $0 }
            }
        } catch {
            guard current(request, target, ticket) else { return }
            if error is CancellationError { back() }
            else { loading = false; failure = error as? ReadFailure ?? .unavailable }
        }
    }
    private func contains(_ target: ClientWorkTarget) -> Bool {
        switch target {
        case .task(let id): tasks?.contains { $0.id == id } == true
        case .conversation(let id): conversations?.contains { $0.id == id } == true
        case .appointment(let id): appointments?.contains { $0.id == id } == true
        }
    }
    private func current(_ request: ClientReadSelection, _ target: ClientWorkTarget, _ ticket: Int) -> Bool {
        revision == ticket && selection == request && selected == target
    }
    @discardableResult func back(expected: ClientReadSelection? = nil) -> Bool {
        if let expected, expected != selection { return false }
        let hadChild = selected != nil
        revision += 1; selected = nil; detail = nil; loading = false; failure = nil
        return hadChild
    }
    var presentation:ClientWorkControl? {selection.map {ClientWorkControl(selection:$0,generation:revision,target:selected)}}
    func matches(_ expected:ClientWorkControl?)->Bool {expected != nil && presentation==expected}
    func open(_ target:ClientWorkTarget,presentation:ClientWorkControl?) async {guard let presentation,matches(presentation),selected==nil,!loading else {return};await open(target,expected:presentation.selection)}
    func retry(presentation:ClientWorkControl?) async {guard let presentation,matches(presentation),!loading,let selected else {return};await open(selected,expected:presentation.selection)}
    @discardableResult func back(presentation:ClientWorkControl?)->Bool {guard let presentation,matches(presentation),selected != nil else {return false};return back(expected:presentation.selection)}
    func clear() { back(); selection = nil; parent = nil; tasks = nil; conversations = nil; appointments = nil }
}
