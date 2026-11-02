import Foundation
import SwiftUI
import CRMCore

// Existing read selections plus local presentation, never server versions or grants.
struct AgendaControl:Equatable {let selection:Selection?;let detail:DetailSelection?;let epoch:Int;let generation:Int;let mode:AgendaMode}

struct AppointmentLifecycleEntryControl:Equatable {let parent:AgendaControl;let related:AppointmentRelationControl?}

@MainActor final class AgendaViewModel: ObservableObject {
    @Published private(set) var session = AgendaSession()
    @Published private(set) var loading = false
    @Published private(set) var detailLoading = false
    @Published private(set) var failure: ReadFailure?
    @Published private(set) var detailFailure: ReadFailure?
    @Published private(set) var businessEpoch = 0
    @Published private(set) var searchRevision = 0
    @Published private var presentationRevision=0
    var control:AgendaControl {AgendaControl(selection:session.selection,detail:session.detailSelection,epoch:businessEpoch,generation:presentationRevision,mode:mode)}
    func matches(_ expected:AgendaControl?)->Bool {expected != nil && control==expected}
    @Published var mode = AgendaMode.list
    @Published var date: Date
    var showsEmptyResult: Bool {
        session.selection != nil && !loading && failure == nil && !session.isPartial && session.responseDay == session.selection?.day && session.items.isEmpty
    }
    let resources:ResourceDirectoryViewModel?
    let services:ServiceDirectoryViewModel?
    func directoryPresentationChanged() {presentationRevision += 1}
    let booking:AppointmentBookingViewModel?
    let lifecycle:AppointmentLifecycleViewModel?
    let relations: AppointmentRelationsViewModel?
    private let repository: any AgendaRepository
    init(repository: any AgendaRepository, initialDate: Date = Date(), relations: AppointmentRelationsViewModel? = nil,lifecyclePort:(any SyntheticAppointmentLifecyclePort)?=nil,lifecycleReferences:(any AppointmentReferenceRepository)?=nil,bookingPort:(any SyntheticAppointmentBookingPort)?=nil,bookingClients:(any ClientProfileRepository)?=nil,bookingReferences:(any AppointmentReferenceRepository)?=nil,serviceRepository:(any ServiceDirectoryRepository)?=nil,resourceRepository:(any ResourceDirectoryRepository)?=nil,bookingServices:(any ServiceDirectoryRepository)?=nil,bookingResources:(any ResourceDirectoryRepository)?=nil,bookingClientSearch:(any ClientSearchRepository)?=nil) {self.resources=resourceRepository.map {ResourceDirectoryViewModel(repository:$0)};self.services=serviceRepository.map {ServiceDirectoryViewModel(repository:$0)}; self.booking=bookingPort.map {AppointmentBookingViewModel(port:$0,clients:bookingClients,references:bookingReferences,services:bookingServices,resources:bookingResources,clientSearch:bookingClientSearch)};self.repository = repository; self.date = initialDate; self.relations = relations;lifecycle=lifecyclePort.map {AppointmentLifecycleViewModel(port:$0,references:lifecycleReferences)} }
    func start() async {
        guard session.businesses.isEmpty, !loading else { return }
        presentationRevision += 1;loading = true; failure = nil
        do {
            let bootstrap = try await repository.bootstrap()
            try session.install(bootstrap)
            await load(business: bootstrap.active_business.id)
        } catch { failure = error as? ReadFailure ?? .unavailable; loading = false }
    }
    func load(business: Int) async {
        resources?.bind(nil);services?.bind(nil);booking?.bind(nil);lifecycle?.bind(nil);relations?.clear()
        do {
            guard let selected = session.businesses.first(where: { $0.id == business }) else { throw ReadFailure.invalidContext }
            let previousBusiness = session.selection?.business.id
            let scope = try session.begin(businessID: business, day: Day.string(date, timezone: selected.timezone))
            if previousBusiness != business { businessEpoch += 1 }
            resources?.bind(resourceOwner);services?.bind(serviceOwner)
            presentationRevision += 1;searchRevision += 1
            detailLoading = false; detailFailure = nil
            loading = true; failure = nil
            do {
                let payload = try await repository.appointments(business: business, day: scope.day)
                if try session.receive(payload, for: scope) { loading = false }
            } catch {
                guard session.selection == scope else { return }
                failure = error is CancellationError ? nil : (error as? ReadFailure ?? .unavailable); loading = false
            }
        } catch { failure = error as? ReadFailure ?? .unavailable; loading = false }
    }
    func loadDetail(id: Int) async {
        resources?.bind(nil);services?.bind(nil);booking?.bind(nil);lifecycle?.bind(nil);relations?.clear()
        guard let scope = session.selection else { return }
        let request: DetailSelection
        do { request = try session.beginDetail(id: id) }
        catch { detailFailure = error as? ReadFailure ?? .unavailable; detailLoading = false; return }
        presentationRevision += 1;detailLoading = true; detailFailure = nil
        do {
            let payload = try await repository.appointment(business: scope.business.id, id: id)
            if try session.receive(payload, for: request) { searchRevision += 1; detailLoading = false; relations?.bind(payload, request: request);lifecycle?.bind(lifecycleSource);booking?.bind(bookingSource) }
        } catch {
            guard session.detailSelection == request else { return }
            detailFailure = error as? ReadFailure ?? .unavailable; detailLoading = false
        }
    }
    func switchBusiness(_ id:Int,expected:AgendaControl?) async {guard matches(expected),session.detailSelection==nil,session.selection?.business.id != id,session.businesses.contains(where:{$0.id==id}) else {return};await load(business:id)}
    func changeDate(_ next:Date,previous:Date,expected:AgendaControl?) async {guard matches(expected),session.detailSelection==nil,date==previous,next != date,let scope=session.selection else {return};date=next;await load(business:scope.business.id)}
    func setMode(_ next:AgendaMode,previous:AgendaMode,expected:AgendaControl?) {guard matches(expected),session.selection != nil,session.detailSelection==nil,mode==previous,next != mode else {return};presentationRevision += 1;mode=next}
    func retryList(expected:AgendaControl?) async {guard matches(expected),!loading,session.detailSelection==nil else {return};if let scope=session.selection {await load(business:scope.business.id)} else {await start()}}
    func openDetail(id:Int,expected:AgendaControl?) async {guard matches(expected),!loading,failure==nil,session.detailSelection==nil,session.items.contains(where:{$0.id==id}) else {return};await loadDetail(id:id)}
    func retryDetail(expected:AgendaControl?) async {guard matches(expected),!detailLoading,let request=session.detailSelection else {return};await loadDetail(id:request.id)}
    func closeDetail(expected:AgendaControl?) {guard matches(expected),session.detailSelection != nil else {return};closeDetail()}
    func closeDetail() {
        booking?.bind(nil);lifecycle?.bind(nil);presentationRevision += 1;relations?.clear(); session.clearDetail();resources?.bind(resourceOwner);services?.bind(serviceOwner); detailLoading = false; detailFailure = nil
    }
}

extension AgendaViewModel {
    var lifecycleSource:AppointmentLifecycleSource? {
        guard !loading,!detailLoading,detailFailure==nil,let read=session.detailSelection,let detail=session.detail,detail.business==read.scope.business.id,detail.appointment.id==read.id else {return nil}
        return AppointmentLifecycleSource(read:read,epoch:businessEpoch,appointment:detail.appointment,linkedResourceID:detail.referenceID(.resource))
    }
    var lifecycleEntryControl:AppointmentLifecycleEntryControl? {
        guard booking?.presented != true,let lifecycle,let source=lifecycleSource,lifecycle.source==source,relations?.selected==nil else {return nil}
        return AppointmentLifecycleEntryControl(parent:control,related:relations?.presentation)
    }
    func matchesLifecycleEntry(_ expected:AppointmentLifecycleEntryControl?)->Bool {expected != nil && lifecycleEntryControl==expected}
    func prepareLifecycle(_ action:AppointmentLifecycleAction,entry:AppointmentLifecycleEntryControl?,child:AppointmentLifecycleControl?) {guard matchesLifecycleEntry(entry) else {return};lifecycle?.prepare(action,expected:child)}
}

struct AppointmentBookingEntryControl:Equatable {let parent:AgendaControl;let related:AppointmentRelationControl?;let lifecycle:AppointmentLifecycleControl?}
extension AgendaViewModel {
    var bookingSource:AppointmentBookingSource? {
        guard !loading,!detailLoading,detailFailure==nil,let read=session.detailSelection,let detail=session.detail,detail.business==read.scope.business.id,detail.appointment.id==read.id,let client=detail.linkedClientID,let service=detail.referenceID(.service) else {return nil}
        return AppointmentBookingSource(read:read,epoch:businessEpoch,clientID:client,serviceID:service,resourceID:detail.referenceID(.resource))
    }
    var bookingEntryControl:AppointmentBookingEntryControl? {guard let booking,booking.source==bookingSource,booking.canPresent,relations?.selected==nil,lifecycle?.review==nil,lifecycle?.reschedulePresented != true else {return nil};return AppointmentBookingEntryControl(parent:control,related:relations?.presentation,lifecycle:lifecycle?.control)}
    func matchesBookingEntry(_ expected:AppointmentBookingEntryControl?)->Bool {expected != nil && bookingEntryControl==expected}
    func openBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?) {guard matchesBookingEntry(entry),booking?.open(expected:child)==true else {return};presentationRevision += 1}
    func backBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?) {guard matchesBookingEntry(entry) else {return};if booking?.back(expected:child)==true {presentationRevision += 1}}
    func acknowledgeBooking(entry:AppointmentBookingEntryControl?,child:AppointmentBookingControl?,record:AppointmentBookingRecord) {guard matchesBookingEntry(entry),let booking,booking.control==child,booking.submission==record else {return};let before=booking.control;booking.acknowledge(expected:child,record:record);if before != booking.control {presentationRevision += 1}}
}

struct AppointmentBookingCandidateControl:Equatable {
    let parent:AgendaControl;let related:AppointmentRelationControl;let slot:AppointmentSlotControl;let review:AppointmentSlotCandidateReview;let booking:AppointmentBookingControl;let lifecycle:AppointmentLifecycleControl?;let time:AppointmentBookingCandidateTime
}
extension AgendaViewModel {
    func bookingCandidateControl(parent:AgendaControl?,related:AppointmentRelationControl?,slot:AppointmentSlotControl?,review:AppointmentSlotCandidateReview)->AppointmentBookingCandidateControl? {
        guard let parent,matches(parent),let source=bookingSource,let booking,booking.source==source,booking.canOpen,let child=booking.control,let links=relations,let related,links.matches(related),links.request==source.read,links.selected == .service(source.serviceID),!links.loading,links.failure==nil,let reference=links.reference,reference.valid(for:source.read.scope.business.id,id:source.serviceID),reference==review.context.service,review.context.business==source.read.scope.business,let slot,links.slotReads.matches(slot),slot.owner==source.read,links.slotReads.presented,!links.slotReads.loading,links.slotReads.failure==nil,links.slotReads.review==review,links.slotReads.context==review.context,links.slotReads.read==review.context.read,review.valid(for:review.context),lifecycle?.review==nil,lifecycle?.reschedulePresented != true,let time=AppointmentBookingCandidateTime(source:source,review:review),booking.permitsCandidate(time) else {return nil}
        return AppointmentBookingCandidateControl(parent:parent,related:related,slot:slot,review:review,booking:child,lifecycle:lifecycle?.control,time:time)
    }
    func useBookingCandidate(_ expected:AppointmentBookingCandidateControl) {
        guard bookingCandidateControl(parent:expected.parent,related:expected.related,slot:expected.slot,review:expected.review)==expected,booking?.openCandidate(expected.time,expected:expected.booking)==true else {return}
        relations?.back(presentation:expected.related);presentationRevision += 1
    }
}
