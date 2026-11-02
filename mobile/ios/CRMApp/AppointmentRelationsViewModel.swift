import Foundation
import SwiftUI
import CRMCore

// Local related-read visit, separate from parent DetailSelection and server authority.
struct AppointmentRelationControl:Equatable {let request:DetailSelection;let generation:Int;let target:AppointmentRelatedTarget?}

@MainActor final class AppointmentRelationsViewModel: ObservableObject {
    let profile: ClientProfileViewModel
    let slotReads:AppointmentSlotReadViewModel
    @Published private(set) var request: DetailSelection?
    @Published private(set) var parent: AppointmentDetail?
    @Published private(set) var tasks: [WorkTask]?
    @Published private(set) var selected: AppointmentRelatedTarget?
    @Published private(set) var task: TaskDetails?
    @Published private(set) var reference:AppointmentReferenceDetail?
    @Published private(set) var loading = false
    @Published private(set) var failure: ReadFailure?
    private let repository: any AppointmentRelatedRepository
    private let references:(any AppointmentReferenceRepository)?
    private var revision = 0
    init(repository: any AppointmentRelatedRepository,references:(any AppointmentReferenceRepository)?=nil,slots:(any AppointmentSlotRepository)?=nil) {self.references=references;slotReads=AppointmentSlotReadViewModel(repository:slots,references:references); self.repository = repository; profile = ClientProfileViewModel(repository: repository) }
    func bind(_ parent: AppointmentDetail, request: DetailSelection) {
        clear()
        guard request.id > 0, request.scope.business.id > 0, parent.business == request.scope.business.id, parent.appointment.id == request.id else { return }
        self.request = request; self.parent = parent; tasks = parent.providedTasks
    }
    func openClient(expected: DetailSelection? = nil) async {
        if let expected, expected != request { return }
        guard let request, let id = parent?.linkedClientID else { return }
        back(); selected = .client(id)
        await profile.load(business: request.scope.business.id, id: id)
    }
    func openTask(_ id: Int, expected: DetailSelection? = nil) async {
        if let expected, expected != request { return }
        guard let request, let parent, tasks?.contains(where: { $0.id == id }) == true else { return }
        back(); selected = .task(id); loading = true; let ticket = revision
        do {
            let result = try await repository.taskDetails(business: request.scope.business.id, id: id)
            guard revision == ticket, self.request == request else { return }
            guard result.valid(for: request.scope.business.id, id: id), result.details.appointment_id == parent.appointment.id else { throw ReadFailure.invalidPayload }
            task = result; loading = false; tasks = tasks?.map { $0.id == id ? result.task : $0 }
        } catch {
            guard revision == ticket, self.request == request else { return }
            if error is CancellationError { back() }
            else { loading = false; failure = error as? ReadFailure ?? .unavailable }
        }
    }
    func referenceAvailable(_ kind:AppointmentReferenceKind)->Bool {references != nil && (request?.revision ?? 0)>0 && (request?.scope.revision ?? 0)>0 && parent?.referenceID(kind) != nil}
    func openReference(_ kind:AppointmentReferenceKind,presentation:AppointmentRelationControl?) async {
        guard let presentation,matches(presentation),selected==nil,referenceAvailable(kind) else {return}
        await loadReference(kind,expected:presentation.request)
    }
    private func loadReference(_ kind:AppointmentReferenceKind,expected:DetailSelection) async {
        guard let request,self.request==expected,let id=parent?.referenceID(kind),let references else {return}
        back();selected=kind == .service ? .service(id):.resource(id);loading=true;let ticket=revision
        do {
            let detail=try await references.reference(kind,business:request.scope.business.id,id:id)
            guard revision==ticket,self.request==request else {return}
            guard detail.valid(for:request.scope.business.id,id:id) else {throw ReadFailure.invalidPayload}
            reference=detail;loading=false
            if kind == .service {slotReads.bind(service:detail,owner:request,linkedID:parent?.referenceID(.resource))}
        } catch {
            guard revision==ticket,self.request==request else {return}
            if error is CancellationError {back()} else {loading=false;failure=error as? ReadFailure ?? .unavailable}
        }
    }
    var presentation:AppointmentRelationControl? {request.map {AppointmentRelationControl(request:$0,generation:revision,target:selected)}}
    func matches(_ expected:AppointmentRelationControl?)->Bool {expected != nil && presentation==expected}
    func openClient(presentation:AppointmentRelationControl?) async {guard let presentation,matches(presentation),selected==nil else {return};await openClient(expected:presentation.request)}
    func openTask(_ id:Int,presentation:AppointmentRelationControl?) async {guard let presentation,matches(presentation),selected==nil else {return};await openTask(id,expected:presentation.request)}
    func retry(presentation:AppointmentRelationControl?) async {guard let presentation,matches(presentation),!loading,!profile.loading,let selected else {return};switch selected {case .client:await openClient(expected:presentation.request);case .task(let id):await openTask(id,expected:presentation.request);case .service:await loadReference(.service,expected:presentation.request);case .resource:await loadReference(.resource,expected:presentation.request)}}
    func back(presentation:AppointmentRelationControl?) {guard matches(presentation),selected != nil else {return};back()}
    func back() { slotReads.clear();revision += 1; selected = nil; task = nil;reference=nil; loading = false; failure = nil; profile.clear() }
    func clear() { back(); request = nil; parent = nil; tasks = nil }
}
