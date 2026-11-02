import Foundation
import SwiftUI
import CRMCore

struct ServiceDirectoryOwner:Equatable {let scope:Selection;let epoch:Int}
struct ServiceDirectoryControl:Equatable {let owner:ServiceDirectoryOwner;let visit:Int}
// Stable for one navigation presentation; async list/detail changes revoke content controls only.
struct ServiceDirectoryPresentation:Equatable {let owner:ServiceDirectoryOwner;let visit:Int}
struct ServiceDirectoryReadChoice:Equatable {let owner:ServiceDirectoryOwner;let listVisit:Int;let detailVisit:Int;let listed:ServiceDirectoryItem;let item:ServiceDirectoryItem}
@MainActor final class ServiceDirectoryViewModel:ObservableObject {
    @Published private(set) var owner:ServiceDirectoryOwner?
    @Published private(set) var presented=false
    @Published private(set) var loading=false
    @Published private(set) var failure:ReadFailure?
    @Published private(set) var window:ServiceDirectoryWindow?
    @Published private(set) var selected:ServiceDirectoryItem?
    @Published private(set) var detail:ServiceDirectoryItem?
    @Published private(set) var choice:ServiceDirectoryReadChoice?
    @Published private var visit=0
    @Published private var presentationVisit=0
    private var listVisit=0
    private let repository:any ServiceDirectoryRepository
    init(repository:any ServiceDirectoryRepository) {self.repository=repository}
    var control:ServiceDirectoryControl? {owner.map {ServiceDirectoryControl(owner:$0,visit:visit)}}
    var presentation:ServiceDirectoryPresentation? {guard presented,let owner else {return nil};return ServiceDirectoryPresentation(owner:owner,visit:presentationVisit)}
    func matches(_ expected:ServiceDirectoryControl?)->Bool {expected != nil && control==expected}
    func matchesPresentation(_ expected:ServiceDirectoryPresentation?)->Bool {expected != nil && presentation==expected}
    private func clear() {loading=false;failure=nil;window=nil;selected=nil;detail=nil;choice=nil}
    func bind(_ next:ServiceDirectoryOwner?) {visit += 1;presentationVisit += 1;presented=false;owner=next;clear()}
    @discardableResult func open(expected:ServiceDirectoryControl?)->Bool {guard matches(expected),owner != nil,!presented else {return false};visit += 1;presentationVisit += 1;clear();presented=true;return true}
    @discardableResult func close(expected:ServiceDirectoryPresentation?)->Bool {guard matchesPresentation(expected) else {return false};visit += 1;presentationVisit += 1;presented=false;clear();return true}
    func reload(expected:ServiceDirectoryControl?) async {
        guard matches(expected),presented,!loading,selected==nil,let owner else {return}
        visit += 1;clear();loading=true;let ticket=control
        do {let value=try await repository.services(business:owner.scope.business.id)
            guard matches(ticket),presented else {return}
            guard value.business==owner.scope.business.id,value.items.allSatisfy({$0.business==value.business}),Set(value.items.map(\.id)).count==value.items.count else {throw ReadFailure.invalidPayload}
            window=value;listVisit=visit;loading=false
        } catch {guard matches(ticket),presented else {return};window=nil;loading=false;failure=error as? ReadFailure ?? .unavailable}
    }
    func select(_ row:ServiceDirectoryItem,expected:ServiceDirectoryControl?) async {
        guard matches(expected),presented,!loading,selected==nil,let owner,let window,window.business==owner.scope.business.id,window.items.contains(row) else {return}
        visit += 1;selected=row;detail=nil;choice=nil;failure=nil;loading=true;let ticket=control
        do {let value=try await repository.service(business:owner.scope.business.id,id:row.id)
            guard matches(ticket),presented else {return}
            guard value.business==owner.scope.business.id,value.id==row.id else {throw ReadFailure.invalidPayload};detail=value;loading=false
        } catch {guard matches(ticket),presented else {return};detail=nil;choice=nil;loading=false;failure=error as? ReadFailure ?? .unavailable}
    }
    func backToWindow(expected:ServiceDirectoryControl?) {guard matches(expected),presented,selected != nil else {return};visit += 1;selected=nil;detail=nil;choice=nil;failure=nil;loading=false}
    func choose(expected:ServiceDirectoryControl?) {guard matches(expected),presented,!loading,failure==nil,choice==nil,let owner,let selected,let detail,detail.business==owner.scope.business.id,detail.id==selected.id else {return};let value=ServiceDirectoryReadChoice(owner:owner,listVisit:listVisit,detailVisit:visit,listed:selected,item:detail);visit += 1;choice=value}
}
extension AgendaViewModel {
    var serviceOwner:ServiceDirectoryOwner? {guard session.detailSelection==nil,let scope=session.selection else {return nil};return ServiceDirectoryOwner(scope:scope,epoch:businessEpoch)}
    var serviceEntry:AgendaControl? {guard resources?.presented != true,let services,services.owner==serviceOwner,serviceOwner != nil,!services.presented else {return nil};return control}
    func openServices(expected:AgendaControl?,child:ServiceDirectoryControl?) async {guard let expected,serviceEntry==expected,matches(expected),let services,services.open(expected:child) else {return};directoryPresentationChanged();await services.reload(expected:services.control)}
    func closeServices(expected:ServiceDirectoryPresentation?) {if services?.close(expected:expected)==true {directoryPresentationChanged()}}
}
