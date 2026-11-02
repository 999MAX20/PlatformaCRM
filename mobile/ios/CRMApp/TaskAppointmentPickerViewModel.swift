import Foundation
import SwiftUI
import CRMCore

// Local read visit, no server version, booking key or CREATE permission.
struct TaskAppointmentPickerControl:Equatable {let context:TaskDraftContext;let generation:Int}
// Input visit remains stable across raw edits; read/choice generations remain independent.
struct TaskAppointmentPickerInputControl:Equatable {let context:TaskDraftContext;let visit:Int}
@MainActor final class TaskAppointmentPickerViewModel:ObservableObject {
    @Published private(set) var context:TaskDraftContext?
    @Published private(set) var day=""
    @Published private(set) var items:[Appointment]=[]
    @Published private(set) var total=0
    @Published private(set) var loaded=false
    @Published private(set) var loading=false
    @Published private(set) var selectedID:Int?
    @Published private(set) var detail:AppointmentDetail?
    @Published private(set) var detailLoading=false
    @Published private(set) var failure:ReadFailure?
    private var generation=0
    @Published private var inputVisit=0
    private let repository:any AgendaRepository
    init(repository:any AgendaRepository) {self.repository=repository}
    var control:TaskAppointmentPickerControl? {context.map {TaskAppointmentPickerControl(context:$0,generation:generation)}}
    func matches(_ expected:TaskAppointmentPickerControl?)->Bool {expected != nil && expected==control}
    var inputControl:TaskAppointmentPickerInputControl? {guard let context,!loading,selectedID==nil else {return nil};return TaskAppointmentPickerInputControl(context:context,visit:inputVisit)}
    func updateDay(_ raw:String,input:TaskAppointmentPickerInputControl?) {guard let input,inputControl==input else {return};updateDay(raw,expected:control)}
    var partial:Bool {loaded && total>items.count}
    var canRead:Bool {context != nil && selectedID==nil && !loading && TaskAppointmentDay.valid(day)}
    func begin(_ next:TaskDraftContext?) {inputVisit += 1;generation += 1;context=next?.valid==true ? next:nil;day="";items=[];total=0;loaded=false;loading=false;selectedID=nil;detail=nil;detailLoading=false;failure=nil}
    func updateDay(_ raw:String,expected:TaskAppointmentPickerControl?) {
        guard matches(expected),!loading,selectedID==nil,day != raw else {return}
        generation += 1;day=raw;items=[];total=0;loaded=false;failure=nil
    }
    func read(expected:TaskAppointmentPickerControl?) async {
        guard matches(expected),canRead,let context else {return}
        inputVisit += 1;generation += 1;let ticket=generation,raw=day;loading=true;loaded=false;items=[];total=0;failure=nil
        do {
            let page=try await repository.appointments(business:context.business,day:raw)
            try Task.checkCancellation()
            guard ticket==generation,self.context==context else {return}
            guard page.business==context.business,page.date==raw,page.items.count<=50,page.summary.total>=page.items.count,
                  page.items.allSatisfy({$0.id>0 && $0.id<=Int(Int32.max)}),Set(page.items.map(\.id)).count==page.items.count else {throw ReadFailure.invalidPayload}
            items=page.items;total=page.summary.total;loaded=true;loading=false
        } catch {guard ticket==generation,self.context==context else {return};loading=false;failure=error as? ReadFailure ?? .unavailable}
        generation += 1
    }
    func open(_ id:Int,expected:TaskAppointmentPickerControl?) async {
        guard matches(expected),loaded,!loading,selectedID==nil,items.contains(where:{$0.id==id}) else {return}
        await loadDetail(id)
    }
    private func loadDetail(_ id:Int) async {
        guard let context else {return};inputVisit += 1;generation += 1;let ticket=generation;selectedID=id;detail=nil;detailLoading=true;failure=nil
        do {
            let value=try await repository.appointment(business:context.business,id:id)
            try Task.checkCancellation()
            guard ticket==generation,self.context==context,selectedID==id else {return}
            guard TaskDraftAppointmentChoice(detail:value,business:context.business,id:id) != nil else {throw ReadFailure.invalidPayload}
            detail=value;detailLoading=false
        } catch {guard ticket==generation,self.context==context,selectedID==id else {return};detailLoading=false;failure=error as? ReadFailure ?? .unavailable}
        generation += 1
    }
    func retryDetail(expected:TaskAppointmentPickerControl?) async {guard matches(expected),!detailLoading,let id=selectedID else {return};await loadDetail(id)}
    func backDetail(expected:TaskAppointmentPickerControl?) {guard matches(expected),selectedID != nil else {return};inputVisit += 1;generation += 1;selectedID=nil;detail=nil;detailLoading=false;failure=nil}
    func choice(expected:TaskAppointmentPickerControl?)->TaskDraftAppointmentChoice? {
        guard matches(expected),!loading,!detailLoading,failure==nil,let context,let id=selectedID,let detail else {return nil}
        return TaskDraftAppointmentChoice(detail:detail,business:context.business,id:id)
    }
}
