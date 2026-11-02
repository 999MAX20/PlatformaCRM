import Foundation
import CRMCore

func runTaskCreateParentChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-parent-cases.json"))) as! [String:Any]
    for row in catalog["choice_cases"] as! [[String:Any]] {
        let detail=try JSONDecoder().decode(TaskDetails.self,from:Data((row["detail_json"] as! String).utf8)),choice=TaskDraftParentChoice(detail:detail,business:row["business"] as! Int,id:row["id"] as! Int)
        try expect((choice != nil)==row["valid"] as! Bool,"Parent independent scoped detail/read contract: \(row["name"]!)")
        if let choice {let title=try JSONDecoder().decode(String?.self,from:Data((row["title_json"] as! String).utf8));try expect(choice.title.map({Data($0.utf8)})==title.map({Data($0.utf8)}) && choice.status==detail.task.status && choice.id==detail.task.id,"Parent title/status/identity normalised or inferred")}
    }
    let repo=APIReadRepository(transport:FixtureTransport(directory:directory)),context=TaskDraftContext(business:101,epoch:1),auth=SyntheticTaskCreateGrant(business:101,actor:9001,create:true).authorization(for:context)!,parent=TaskDraftParentChoice(detail:try await repo.taskDetails(business:101,id:1101),business:101,id:1101)!,foreign=TaskDraftParentChoice(detail:try await repo.taskDetails(business:202,id:1201),business:202,id:1201)!,client=TaskDraftClientChoice(profile:try await repo.clientProfile(business:101,id:701),business:101,id:701)!,appointment=TaskDraftAppointmentChoice(detail:try await repo.appointment(business:101,id:501),business:101,id:501)!
    func editor(_ selected:TaskDraftParentChoice?)->TaskDraftSession {
        var s=TaskDraftSession();s.bind(context);_=s.open(expected:context);let q=s.selection!;s.update(.title,value:"  Manual child task\n",expected:q);s.update(.description,value:"  Keep original child notes\n",expected:q);s.chooseDue(.setDate,expected:q);s.update(.dueAt,value:"2026-11-02T09:30:00+05:00",expected:q);s.chooseReminder(.setDate,expected:q);s.update(.reminderAt,value:"2026-11-01T14:00:00Z",expected:q);s.chooseClient(client,expected:q);s.chooseAppointment(appointment,expected:q);s.chooseParent(selected,expected:q);return s
    }
    var s=editor(parent);let before=s.values;s.chooseParent(foreign,expected:s.selection!);try expect(s.values==before,"Foreign Parent overwrote composer")
    s.chooseParent(nil,expected:s.selection!);try expect(s.values.parentTask==nil && s.values.client==before.client && s.values.appointment==before.appointment && s.values.title==before.title && s.values.description==before.description && s.values.dueDate==before.dueDate && s.values.reminderDate==before.reminderDate,"Removing unsent parent inferred/lost other relations or raw fields")
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var s=editor(row["selected"] is NSNull ? nil:parent);try expect(s.prepare(expected:s.selection!),"Parent could not review valid optional relation");let review=s.review!;var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:review,authorization:auth)!,body=a.preparedBody()!,payload=try JSONSerialization.jsonObject(with:body) as! [String:Any]
        try expect(payload["parent_task_id"]==nil && payload["parent_task"] as? Int==review.preview.parentTaskID && payload["client"] as? Int==701 && payload["appointment"] as? Int==501 && payload["due_at"] as? String==review.preview.dueAt && payload["reminder_at"] as? String==review.preview.reminderAt,"Generic parent_task omitted/renamed or independent inputs inferred")
        try expect(a.preparedBody()==body && a.review.values==review.values,"Parent immutable raw/body snapshot changed")
        let read=TaskCreateParentRead.decode(Data((row["body_json"] as! String).utf8)),kind=row["kind"] as! String,expected:TaskCreateParentRead=kind=="parent" ? .parent(row["id"] as! Int):kind=="notSet" ? .notSet:.unknown
        try expect(read==expected,"Parent generic FK receipt coerced/aliased: \(row["name"]!)")
        let v=review.preview,task=WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:v.dueAt,business:101,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:9001,created_at:"2026-10-30T12:00:00Z")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,task:task,reminderAt:v.reminderAt,clientRead:.client(row["client_echo"] as! Int),appointmentRead:.appointment(row["appointment_echo"] as! Int),parentRead:read));let record=ledger.visible(auth)!,yes=row["accepted"] as! Bool
        try expect((record.phase == .confirmed)==yes && record.parentTaskID==(yes ? v.parentTaskID:nil),"Unverified selected Parent/Client/Appointment became fake success: \(row["name"]!)")
        if !yes {try expect(ledger.blocked(context) && !ledger.acknowledge(auth) && ledger.begin(review:review,authorization:auth)==nil && record.attempt.preparedBody()==body && record.attempt.review.values==review.values,"Unknown parent lost full raw/relation/attempt/body or replayed")}
    }
    var fake=editor(parent);_=fake.prepare(expected:fake.selection!);var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:fake.review!,authorization:auth)!;ledger.complete(a,outcome:try await FixtureTaskCreatePort(directory:directory).execute(a));try expect(ledger.visible(auth)?.phase == .confirmed && ledger.visible(auth)?.parentTaskID==1101 && ledger.visible(auth)?.clientID==701 && ledger.visible(auth)?.appointmentID==501,"Separate fake port failed exact three generic FKs")
    return count
}
