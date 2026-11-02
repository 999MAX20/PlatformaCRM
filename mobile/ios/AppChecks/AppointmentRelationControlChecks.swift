import Foundation
import CRMCore

@MainActor func checkAppointmentRelationControls(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),source=ControlledAppointmentRelations(directory:directory)
    let links=AppointmentRelationsViewModel(repository:source),m=AgendaViewModel(repository:source,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:links)
    try expect(links.presentation==nil && !links.matches(nil),"Missing parent yielded child control")
    await m.start();m.setMode(.calendar,previous:.list,expected:m.control);await m.openDetail(id:501,expected:m.control)
    let parent=m.session.detailSelection!,scope=m.session.selection,notes=m.session.detail?.details.notes,entry=links.presentation!
    let profile=try await repo.clientProfile(business:101,id:7001),task=try await repo.taskDetails(business:101,id:1301)
    let open=Task {await links.openClient(presentation:entry)};await source.wait(profiles:1,tasks:0);let clientVisit=links.presentation!
    await links.openClient(presentation:entry);await links.openTask(1301,presentation:entry);await links.retry(presentation:clientVisit);links.back(presentation:entry)
    try expect(await source.counts()==[1,0] && links.selected == .client(7001),"Old parent/pending Client callbacks repeated/switched read")
    await source.profile(0,.failure(.denied));await open.value
    let retry=Task {await links.retry(presentation:links.presentation)};await source.wait(profiles:2,tasks:0);let newer=links.presentation!
    links.back(presentation:clientVisit);await links.retry(presentation:clientVisit)
    await source.profile(1,.success(profile));await retry.value
    try expect(await source.counts()==[2,0] && links.presentation==newer && links.profile.detail?.client.id==7001 && m.session.detailSelection==parent,"Old child Back/retry affected new profile or parent")
    links.back(presentation:newer);let returned=links.presentation!;await links.openTask(999,presentation:returned)
    let first=Task {await links.openTask(1301,presentation:returned)};await source.wait(profiles:2,tasks:1);let old=links.presentation!;links.back(presentation:old)
    let second=Task {await links.openTask(1301,presentation:links.presentation)};await source.wait(profiles:2,tasks:2);let current=links.presentation!
    links.back(presentation:old);await links.retry(presentation:old);await source.task(1,.success(task));await second.value;await source.task(0,.failure(.denied));await first.value
    try expect(await source.counts()==[2,2] && links.presentation==current && links.task?.task.id==1301 && links.failure==nil && m.session.selection==scope && m.mode == .calendar && m.session.detail?.details.notes==notes,"Old Task visit/reply changed current child or parent day/mode/notes")
    links.back(presentation:current);let late=Task {await links.openTask(1301,presentation:links.presentation)};await source.wait(profiles:2,tasks:3);let oldParent=links.presentation!
    await m.retryDetail(expected:m.control);await source.task(2,.success(task));await late.value
    await links.openClient(presentation:oldParent);await links.openTask(1301,presentation:oldParent);links.back(presentation:oldParent)
    try expect(await source.counts()==[2,3] && links.request != parent && links.selected==nil && links.task==nil && links.profile.detail==nil,"Parent refresh accepted old child data/control")
    return count
}
