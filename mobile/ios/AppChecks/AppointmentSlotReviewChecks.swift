import Foundation
import CRMCore

@MainActor func checkAppointmentSlotReview(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw ViewModelCheckFailure(message:message)};count += 1}
    let fixed=APIReadRepository(transport:FixtureTransport(directory:directory)),refs=APIAppointmentReferenceRepository(transport:FixtureTransport(directory:directory)),slots=ControlledAppointmentSlots(),links=AppointmentRelationsViewModel(repository:fixed,references:refs,slots:slots),parent=AgendaViewModel(repository:fixed,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:links)
    await parent.start();await parent.loadDetail(id:501);await links.openReference(.service,presentation:links.presentation)
    let model=links.slotReads,encoder=JSONEncoder();encoder.outputFormatting=[.sortedKeys];let original=try encoder.encode(parent.session.detail),selection=parent.session.selection,list=parent.session.items,owner=parent.control
    model.open(model.presentation);model.setDay("2026-11-02",expected:model.presentation);model.choose(.linked,expected:model.presentation)
    let pending=Task {await model.submit(model.presentation)};await slots.wait(0);let loading=model.presentation!;model.selectCandidate(0,expected:loading);try expect(model.review==nil,"Pending read accepted a candidate/default selection")
    let intent=(await slots.recorded())[0],data=Data("[{\"start_at\":\"2026-11-02T04:15:00Z\",\"end_at\":\"2026-11-02T05:00:00Z\"},{\"start_at\":\"2026-11-02T06:30:00Z\",\"end_at\":\"2026-11-02T07:10:00Z\"}]".utf8),answer=AppointmentSlotRead.decode(data,intent:intent)!
    await slots.resolve(0,answer);await pending.value;let results=model.presentation!,context=model.context!
    model.selectCandidate(-1,expected:results);model.selectCandidate(2,expected:results);try expect(model.review==nil && model.presentation==results,"Out of window candidate changed read presentation")
    model.selectCandidate(1,expected:results);let reviewControl=model.presentation!,review=model.review!
    try expect(review.index==1 && review.candidate==answer.candidates[1] && review.context.service==links.reference && review.context.resource?.id==9001 && review.context.business==parent.session.selection?.business,"Review lost independently read identities or selected default range")
    model.selectCandidate(0,expected:results);model.backToCandidates(results);model.edit(results)
    try expect(model.review==review && model.presentation==reviewControl,"Old list callbacks displaced current review")
    let before=await slots.recorded().count;model.backToCandidates(reviewControl);let reopened=model.presentation!;model.selectCandidate(0,expected:reviewControl)
    try expect(model.review==nil && model.context==context && model.read==answer && model.presentation==reopened,"Review Back lost same returned list or admitted old review action")
    try expect(await slots.recorded().count==before,"Back unexpectedly reread/reserved candidate")
    model.selectCandidate(0,expected:reopened);let oldChoice=model.presentation!;let refresh=Task {await model.refresh(oldChoice)};await slots.wait(1)
    try expect(model.review==nil && model.context==nil && model.read==nil && model.day=="2026-11-02" && model.resourceMode == .linked,"Manual reread retained previous selected proof or changed explicit input")
    model.selectCandidate(1,expected:oldChoice);model.backToCandidates(oldChoice);await model.refresh(oldChoice);let calls=await slots.recorded();try expect(calls.count==2 && calls[0]==calls[1],"Reread changed query or repeated stale action")
    await slots.resolve(1,answer);await refresh.value;let current=model.presentation!;model.selectCandidate(1,expected:results);model.selectCandidate(1,expected:oldChoice)
    try expect(model.review==nil && model.context==context && model.presentation==current,"Matching reread restored old selection/accepted old membership ticket")
    model.selectCandidate(0,expected:current);try expect(model.review?.index==0,"Fresh explicit current candidate selection unavailable")
    let currentBody=try encoder.encode(parent.session.detail);try expect(currentBody==original && parent.control==owner && parent.session.items==list && parent.session.selection==selection,"Read review mutated Appointment/list/day/owner")
    model.edit(model.presentation);try expect(model.review==nil && model.context==nil && model.day=="2026-11-02" && model.resourceMode == .linked,"Edit retained candidate context or lost raw intent")
    let denied=Task {await model.submit(model.presentation)};await slots.wait(2);await slots.fail(2,.denied);await denied.value;let errorControl=model.presentation!;model.selectCandidate(0,expected:errorControl)
    try expect(model.review==nil && model.context==nil && model.failure == .denied,"Denied reread became old successful review")
    let retry=Task {await model.retry(errorControl)};await slots.wait(3);await slots.resolve(3,AppointmentSlotRead.decode(Data("[]".utf8),intent:(await slots.recorded())[3])!);await retry.value;model.selectCandidate(0,expected:model.presentation)
    try expect(model.review==nil && model.context?.read.candidates.isEmpty==true,"Empty read selected a default candidate")
    let late=Task {await model.refresh(model.presentation)};await slots.wait(4);let previous=model.presentation;await parent.retryDetail(expected:parent.control);await slots.resolve(4,answer);await late.value;model.selectCandidate(0,expected:previous)
    try expect(model.review==nil && model.context==nil && model.presentation==nil && !model.available,"Parent refresh revived late old read/review")
    // A real independently verified202 fixture variant must retain its own object labels.
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("appointment-reference-read-cases.json"))) as! [String:Any],variant=Data((catalog["parent_202_variant_json"] as! String).utf8),transport=AppointmentReferenceTransport(directory,variant:variant),repo=APIReadRepository(transport:transport),other=AppointmentRelationsViewModel(repository:repo,references:APIAppointmentReferenceRepository(transport:transport),slots:APIAppointmentSlotRepository(transport:FixtureAppointmentSlotTransport(directory:directory))),vm=AgendaViewModel(repository:repo,initialDate:Appointment.instant("2026-10-28T07:00:00Z")!,relations:other)
    await vm.start();await vm.load(business:202);await vm.loadDetail(id:601);await other.openReference(.service,presentation:other.presentation);let child=other.slotReads;child.open(child.presentation);child.setDay("2026-11-02",expected:child.presentation);child.choose(.linked,expected:child.presentation);await child.submit(child.presentation);child.selectCandidate(0,expected:child.presentation)
    try expect(child.review?.context.business.id==202 && child.review?.context.service.id==8002 && child.review?.context.resource?.id==9002 && child.review?.context.service.isActive==false,"202 read review defaulted to101/first/active or unverified label")
    let old202=child.presentation;await vm.load(business:101);child.backToCandidates(old202);child.selectCandidate(0,expected:old202)
    try expect(child.context==nil && child.review==nil && child.presentation==nil,"Business switch admitted old review controls")
    return count
}
