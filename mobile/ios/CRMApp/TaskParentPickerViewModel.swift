import Foundation
import SwiftUI
import CRMCore

// Explicit existing Task list/detail read visit, no CREATE/lifecycle authority.
struct TaskParentPickerControl:Equatable {let context:TaskDraftContext;let generation:Int}
@MainActor final class TaskParentPickerViewModel:ObservableObject {
    @Published private(set) var context:TaskDraftContext?
    @Published private(set) var items:[WorkTask]=[]
    @Published private(set) var total=0
    @Published private(set) var loaded=false
    @Published private(set) var loading=false
    @Published private(set) var selectedID:Int?
    @Published private(set) var detail:TaskDetails?
    @Published private(set) var detailLoading=false
    @Published private(set) var failure:ReadFailure?
    private var generation=0
    private let repository:any TaskReadRepository
    init(repository:any TaskReadRepository) {self.repository=repository}
    var control:TaskParentPickerControl? {context.map {TaskParentPickerControl(context:$0,generation:generation)}}
    func matches(_ expected:TaskParentPickerControl?)->Bool {expected != nil && expected==control}
    var partial:Bool {loaded && total>items.count}
    var canRead:Bool {context != nil && selectedID==nil && !loading}
    func begin(_ next:TaskDraftContext?) {generation += 1;context=next?.valid==true ? next:nil;items=[];total=0;loaded=false;loading=false;selectedID=nil;detail=nil;detailLoading=false;failure=nil}
    func read(expected:TaskParentPickerControl?) async {
        guard matches(expected),canRead,let context else {return}
        generation += 1;let ticket=generation;loading=true;loaded=false;items=[];total=0;failure=nil
        do {
            let page=try await repository.tasks(business:context.business)
            try Task.checkCancellation()
            guard ticket==generation,self.context==context else {return}
            guard page.valid(for:context.business),page.items.count<=50,
                  page.items.allSatisfy({$0.id>0 && $0.id<=Int(Int32.max)}),Set(page.items.map(\.id)).count==page.items.count else {throw ReadFailure.invalidPayload}
            items=page.items;total=page.summary.total;loaded=true;loading=false
        } catch {guard ticket==generation,self.context==context else {return};loading=false;failure=error as? ReadFailure ?? .unavailable}
        generation += 1
    }
    func open(_ id:Int,expected:TaskParentPickerControl?) async {
        guard matches(expected),loaded,!loading,selectedID==nil,items.contains(where:{$0.id==id}) else {return}
        await loadDetail(id)
    }
    private func loadDetail(_ id:Int) async {
        guard let context else {return};generation += 1;let ticket=generation;selectedID=id;detail=nil;detailLoading=true;failure=nil
        do {
            let value=try await repository.taskDetails(business:context.business,id:id)
            try Task.checkCancellation()
            guard ticket==generation,self.context==context,selectedID==id else {return}
            guard TaskDraftParentChoice(detail:value,business:context.business,id:id) != nil else {throw ReadFailure.invalidPayload}
            detail=value;detailLoading=false
        } catch {guard ticket==generation,self.context==context,selectedID==id else {return};detailLoading=false;failure=error as? ReadFailure ?? .unavailable}
        generation += 1
    }
    func retryDetail(expected:TaskParentPickerControl?) async {guard matches(expected),!detailLoading,let id=selectedID else {return};await loadDetail(id)}
    func backDetail(expected:TaskParentPickerControl?) {guard matches(expected),selectedID != nil else {return};generation += 1;selectedID=nil;detail=nil;detailLoading=false;failure=nil}
    func choice(expected:TaskParentPickerControl?)->TaskDraftParentChoice? {
        guard matches(expected),!loading,!detailLoading,failure==nil,let context,let id=selectedID,let detail else {return nil}
        return TaskDraftParentChoice(detail:detail,business:context.business,id:id)
    }
}
