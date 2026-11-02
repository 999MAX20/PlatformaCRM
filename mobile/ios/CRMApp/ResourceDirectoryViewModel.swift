import Foundation
import SwiftUI
import CRMCore

struct ResourceDirectoryOwner:Equatable {let scope:Selection;let epoch:Int}
struct ResourceDirectoryControl:Equatable {let owner:ResourceDirectoryOwner;let visit:Int}
// Stable for one navigation presentation; async list/detail changes revoke content controls only.
struct ResourceDirectoryPresentation:Equatable {let owner:ResourceDirectoryOwner;let visit:Int}
struct ResourceDirectoryReadChoice:Equatable {let owner:ResourceDirectoryOwner;let listVisit:Int;let detailVisit:Int;let listed:ResourceDirectoryItem;let item:ResourceDirectoryItem}
@MainActor final class ResourceDirectoryViewModel:ObservableObject {
    @Published private(set) var owner:ResourceDirectoryOwner?
    @Published private(set) var presented=false
    @Published private(set) var loading=false
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var window:ResourceDirectoryWindow?
    @Published private(set) var selected:ResourceDirectoryItem?
    @Published private(set) var detail:ResourceDirectoryItem?
    @Published private(set) var choice:ResourceDirectoryReadChoice?
    @Published private var visit=0
    @Published private var presentationVisit=0
    private var listVisit=0
    private let repository:any ResourceDirectoryRepository
    init(repository:any ResourceDirectoryRepository) {self.repository=repository}
    var control:ResourceDirectoryControl? {owner.map {ResourceDirectoryControl(owner:$0,visit:visit)}}
    var presentation:ResourceDirectoryPresentation? {guard presented,let owner else {return nil};return ResourceDirectoryPresentation(owner:owner,visit:presentationVisit)}
    func matches(_ expected:ResourceDirectoryControl?)->Bool {expected != nil && control==expected}
    func matchesPresentation(_ expected:ResourceDirectoryPresentation?)->Bool {expected != nil && presentation==expected}
    private func clear() {loading=false;failure=nil;window=nil;selected=nil;detail=nil;choice=nil}
    func bind(_ next:ResourceDirectoryOwner?) {visit += 1;presentationVisit += 1;presented=false;owner=next;clear()}
    @discardableResult func open(expected:ResourceDirectoryControl?)->Bool {guard matches(expected),owner != nil,!presented else {return false};visit += 1;presentationVisit += 1;clear();presented=true;return true}
    @discardableResult func close(expected:ResourceDirectoryPresentation?)->Bool {guard matchesPresentation(expected) else {return false};visit += 1;presentationVisit += 1;presented=false;clear();return true}
    func reload(expected:ResourceDirectoryControl?) async {
        guard matches(expected),presented,!loading,selected==nil,let owner else {return}
        visit += 1;clear();loading=true;let ticket=control
        do {let value=try await repository.resources(business:owner.scope.business.id)
            guard matches(ticket),presented else {return}
            guard value.business==owner.scope.business.id,value.items.allSatisfy({$0.business==value.business}),Set(value.items.map(\.id)).count==value.items.count else {throw ReadFailure.invalidPayload}
            window=value;listVisit=visit;loading=false
        } catch {guard matches(ticket),presented else {return};window=nil;loading=false;failure=error as? ReadFailure ?? .unavailable}
    }
    func select(_ row:ResourceDirectoryItem,expected:ResourceDirectoryControl?) async {
        guard matches(expected),presented,!loading,selected==nil,let owner,let window,window.business==owner.scope.business.id,window.items.contains(row) else {return}
        visit += 1;selected=row;detail=nil;choice=nil;failure=nil;loading=true;let ticket=control
        do {let value=try await repository.resource(business:owner.scope.business.id,id:row.id)
            guard matches(ticket),presented else {return}
            guard value.business==owner.scope.business.id,value.id==row.id else {throw ReadFailure.invalidPayload};detail=value;loading=false
        } catch {guard matches(ticket),presented else {return};detail=nil;choice=nil;loading=false;failure=error as? ReadFailure ?? .unavailable}
    }
    func backToWindow(expected:ResourceDirectoryControl?) {guard matches(expected),presented,selected != nil else {return};visit += 1;selected=nil;detail=nil;choice=nil;failure=nil;loading=false}
    func choose(expected:ResourceDirectoryControl?) {guard matches(expected),presented,!loading,failure==nil,choice==nil,let owner,let selected,let detail,detail.business==owner.scope.business.id,detail.id==selected.id else {return};let value=ResourceDirectoryReadChoice(owner:owner,listVisit:listVisit,detailVisit:visit,listed:selected,item:detail);visit += 1;choice=value}
}
extension AgendaViewModel {
    var resourceOwner:ResourceDirectoryOwner? {guard session.detailSelection==nil,let scope=session.selection else {return nil};return ResourceDirectoryOwner(scope:scope,epoch:businessEpoch)}
    var resourceEntry:AgendaControl? {guard services?.presented != true,let resources,resources.owner==resourceOwner,resourceOwner != nil,!resources.presented else {return nil};return control}
    func openResources(expected:AgendaControl?,child:ResourceDirectoryControl?) async {guard let expected,resourceEntry==expected,matches(expected),let resources,resources.open(expected:child) else {return};directoryPresentationChanged();await resources.reload(expected:resources.control)}
    func closeResources(expected:ResourceDirectoryPresentation?) {if resources?.close(expected:expected)==true {directoryPresentationChanged()}}
}
