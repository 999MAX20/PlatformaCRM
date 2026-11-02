import Foundation
import SwiftUI
import CRMCore

enum AppointmentSlotResourceMode:Equatable {case unspecified,linked}
struct AppointmentSlotControl:Equatable {let owner:DetailSelection;let generation:Int}
struct AppointmentSlotInputControl:Equatable {let owner:DetailSelection;let visit:Int}
@MainActor final class AppointmentSlotReadViewModel:ObservableObject {
    @Published private(set) var presented=false
    @Published private(set) var day=""
    @Published private(set) var resourceMode:AppointmentSlotResourceMode?
    @Published private(set) var loading=false
    @Published private(set) var read:AppointmentSlotRead?
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var context:AppointmentSlotReadContext?
    @Published private(set) var review:AppointmentSlotCandidateReview?
    private let repository:(any AppointmentSlotRepository)?
    private let references:(any AppointmentReferenceRepository)?
    private var owner:DetailSelection?;private var service:AppointmentReferenceDetail?;private var linkedID:Int?;private var generation=0;private var inputVisit=0
    init(repository:(any AppointmentSlotRepository)?,references:(any AppointmentReferenceRepository)?) {self.repository=repository;self.references=references}
    func bind(service:AppointmentReferenceDetail,owner:DetailSelection,linkedID:Int?) {
        clear();guard owner.revision>0,owner.scope.revision>0,service.valid(for:owner.scope.business.id,id:service.id) else {return}
        self.owner=owner;self.service=service;self.linkedID=linkedID.flatMap {$0>0 && $0<=Int(Int32.max) ? $0:nil}
    }
    var presentation:AppointmentSlotControl? {owner.map {AppointmentSlotControl(owner:$0,generation:generation)}}
    func matches(_ expected:AppointmentSlotControl?)->Bool {expected != nil && expected==presentation}
    var available:Bool {repository != nil && owner != nil && service != nil}
    var inputControl:AppointmentSlotInputControl? {guard editing,let owner else {return nil};return AppointmentSlotInputControl(owner:owner,visit:inputVisit)}
    func setDayInput(_ value:String,input:AppointmentSlotInputControl?) {guard let input,inputControl==input,!SourceTextIdentity.same(day,value) else {return};day=value;generation += 1}
    var linkedResourceAvailable:Bool {references != nil && linkedID != nil}
    var editing:Bool {presented && !loading && read==nil && failure==nil}
    var canRead:Bool {
        guard editing,repository != nil,let owner,let service,let resourceMode,AppointmentSlotIntent(business:owner.scope.business,service:service,resource:nil,day:day) != nil else {return false}
        return resourceMode == .unspecified || linkedResourceAvailable
    }
    func open(_ expected:AppointmentSlotControl?) {guard matches(expected),available,!presented else {return};generation += 1;inputVisit += 1;presented=true;day="";resourceMode=nil;read=nil;failure=nil}
    func setDay(_ value:String,expected:AppointmentSlotControl?) {guard matches(expected),editing else {return};generation += 1;day=value}
    func choose(_ mode:AppointmentSlotResourceMode,expected:AppointmentSlotControl?) {guard matches(expected),editing,mode == .unspecified || linkedResourceAvailable else {return};generation += 1;resourceMode=mode}
    func edit(_ expected:AppointmentSlotControl?) {guard matches(expected),presented,!loading else {return};generation += 1;inputVisit += 1;read=nil;failure=nil;context=nil;review=nil}
    func close(_ expected:AppointmentSlotControl?) {guard matches(expected),presented else {return};reset()}
    private func reset() {generation += 1;inputVisit += 1;presented=false;day="";resourceMode=nil;loading=false;read=nil;failure=nil;context=nil;review=nil}
    func clear() {reset();owner=nil;service=nil;linkedID=nil}
    func retry(_ expected:AppointmentSlotControl?) async {guard matches(expected),failure != nil,!loading else {return};edit(expected);await submit(presentation)}
    func selectCandidate(_ index:Int,expected:AppointmentSlotControl?) {
        guard matches(expected),presented,!loading,failure==nil,review==nil,let context,read==context.read,let selected=context.review(index:index) else {return}
        generation += 1;review=selected
    }
    func backToCandidates(_ expected:AppointmentSlotControl?) {
        guard matches(expected),!loading,let context,review?.valid(for:context)==true else {return}
        generation += 1;review=nil
    }
    func refresh(_ expected:AppointmentSlotControl?) async {
        guard matches(expected),presented,!loading,failure==nil,context != nil else {return}
        edit(expected);await submit(presentation)
    }
    func submit(_ expected:AppointmentSlotControl?) async {
        guard matches(expected),canRead,let repository,let owner,let service,let mode=resourceMode else {return}
        let rawDay=day;generation += 1;inputVisit += 1;let ticket=generation;loading=true
        do {
            var resource:AppointmentReferenceDetail?
            if mode == .linked {
                guard let references,let linkedID else {throw ReadFailure.invalidContext}
                resource=try await references.reference(.resource,business:owner.scope.business.id,id:linkedID)
                guard ticket==generation,self.owner==owner else {return}
                guard resource?.valid(for:owner.scope.business.id,id:linkedID)==true else {throw ReadFailure.invalidPayload}
            }
            guard let intent=AppointmentSlotIntent(business:owner.scope.business,service:service,resource:resource,day:rawDay) else {throw ReadFailure.invalidContext}
            let result=try await repository.slots(intent)
            guard ticket==generation,self.owner==owner else {return}
            guard result.valid(for:intent) else {throw ReadFailure.invalidPayload}
            guard let context=AppointmentSlotReadContext(business:owner.scope.business,service:service,resource:resource,read:result) else {throw ReadFailure.invalidPayload}
            self.context=context;read=context.read;review=nil;loading=false
        } catch {
            guard ticket==generation,self.owner==owner else {return}
            loading=false;failure=error as? ReadFailure ?? .unavailable
        }
    }
}
