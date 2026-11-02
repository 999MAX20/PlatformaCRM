import Foundation
import CRMCore

private actor ControlledAgendaControls:AgendaRepository {
    let fixture:APIReadRepository
    private var pages:[CheckedContinuation<AppointmentList,any Error>]=[]
    private var details:[CheckedContinuation<AppointmentDetail,any Error>]=[]
    init(_ directory:URL) {fixture=APIReadRepository(transport:FixtureTransport(directory:directory))}
    func bootstrap() async throws -> Bootstrap {try await fixture.bootstrap()}
    func appointments(business:Int,day:String) async throws -> AppointmentList {try await withCheckedThrowingContinuation {pages.append($0)}}
    func appointment(business:Int,id:Int) async throws -> AppointmentDetail {try await withCheckedThrowingContinuation {details.append($0)}}
    func wait(_ p:Int,_ d:Int) async {while pages.count<p || details.count<d {await Task.yield()}}
    func page(_ i:Int,_ value:AppointmentList) {pages[i].resume(returning:value)}
    func detail(_ i:Int,_ value:AppointmentDetail) {details[i].resume(returning:value)}
    func counts()->[Int] {[pages.count,details.count]}
}

@MainActor func checkAgendaControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),source=ControlledAgendaControls(directory)
    let a=try await repo.appointments(business:101,day:"2026-10-28"),b=try await repo.appointments(business:202,day:"2026-10-28"),detail=try await repo.appointment(business:101,id:501)
    let initial=Appointment.instant("2026-10-28T07:00:00Z")!,m=AgendaViewModel(repository:source,initialDate:initial),bootstrap=m.control
    let start=Task {await m.start()};await source.wait(1,0);let pending=m.control
    await m.retryList(expected:pending);await m.openDetail(id:501,expected:pending)
    try expect(await source.counts()==[1,0] && m.loading,"Pending Agenda repeated list/detail")
    await source.page(0,a);await start.value;let list=m.control,items=m.session.items,epoch=m.businessEpoch
    await m.retryList(expected:bootstrap);m.setMode(.calendar,previous:.list,expected:list);let calendar=m.control
    m.setMode(.list,previous:.calendar,expected:list);try expect(m.mode == .calendar,"Old mode callback changed new calendar")
    m.setMode(.list,previous:.calendar,expected:calendar);await m.openDetail(id:501,expected:list)
    try expect(await source.counts()==[1,0] && m.session.items==items && m.session.selection==list.selection,"Mode round trip reused old row control or changed read snapshot")
    let open=Task {await m.openDetail(id:501,expected:m.control)};await source.wait(1,1);let card=m.control
    await m.openDetail(id:501,expected:list);await m.retryList(expected:list);await m.retryDetail(expected:card)
    try expect(await source.counts()==[1,1] && m.detailLoading,"Old list/pending detail repeated request")
    await source.detail(0,detail);await open.value;m.closeDetail(expected:card);let returned=m.control
    await m.openDetail(id:501,expected:list);try expect(await source.counts()==[1,1] && m.session.detail==nil,"Old row reopened returned list")
    let leaving=Task {await m.openDetail(id:501,expected:returned)};await source.wait(1,2);let oldVisit=m.control;m.closeDetail(expected:oldVisit)
    let reopened=Task {await m.openDetail(id:501,expected:m.control)};await source.wait(1,3);let newVisit=m.control
    m.closeDetail(expected:oldVisit);await m.retryDetail(expected:oldVisit)
    var json=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-101-501.json"))) as! [String:Any]
    var row=json["appointment"] as! [String:Any];row["title"]=NSNull();row["start_at"]=NSNull();row["end_at"]=NSNull();json["appointment"]=row
    let withheld=try JSONDecoder().decode(AppointmentDetail.self,from:JSONSerialization.data(withJSONObject:json))
    await source.detail(2,withheld);await reopened.value;await source.detail(1,detail);await leaving.value
    try expect(await source.counts()==[1,3] && m.control==newVisit && m.session.detail != nil && m.detailFailure==nil && m.session.detail?.appointment.title==nil && m.session.items.first?.start_at==nil,"Old same-ID Back/retry/reply changed new raw detail or fabricated withheld time")
    m.closeDetail(expected:newVisit);let beforeDate=m.control,nextDate=Appointment.instant("2026-10-29T07:00:00Z")!
    let change=Task {await m.changeDate(nextDate,previous:initial,expected:beforeDate)};await source.wait(2,3)
    await m.changeDate(initial,previous:nextDate,expected:beforeDate);await m.retryList(expected:m.control)
    await source.page(1,a);await change.value
    try expect(m.businessEpoch==epoch && m.session.selection?.day=="2026-10-29" && m.session.sourceDayMismatch && !m.showsEmptyResult && m.session.items==a.items,"Day change altered Business epoch, accepted old date callback or discarded explicit source mismatch/raw rows")
    let old=m.control,switchB=Task {await m.switchBusiness(202,expected:old)};await source.wait(3,3)
    await m.switchBusiness(101,expected:old);let switchA=Task {await m.switchBusiness(101,expected:m.control)};await source.wait(4,3)
    await source.page(3,a);await switchA.value;await source.page(2,b);await switchB.value
    await m.openDetail(id:501,expected:old);await m.retryList(expected:old);m.setMode(.calendar,previous:.list,expected:old)
    try expect(await source.counts()==[4,3] && m.session.selection?.business.id==101 && m.businessEpoch>epoch && m.mode == .list && m.session.items==a.items,"Business round trip accepted old owner control/late list")
    return count
}
