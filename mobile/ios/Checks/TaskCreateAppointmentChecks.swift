import Foundation
import CRMCore

func runTaskCreateAppointmentChecks(directory:URL) async throws -> Int {
    var count=0
    func expect(_ value:Bool,_ message:String) throws {guard value else {throw CheckFailure(message:message)};count += 1}
    let catalog=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("task-create-appointment-cases.json"))) as! [String:Any]
    for row in catalog["day_cases"] as! [[String:Any]] {
        let day=try JSONDecoder().decode(String.self,from:Data((row["day_json"] as! String).utf8))
        try expect(TaskAppointmentDay.valid(day)==row["valid"] as! Bool,"Explicit Appointment day accepted default/normalized date: \(row["day_json"]!)")
    }
    for row in catalog["choice_cases"] as! [[String:Any]] {
        let detail=try JSONDecoder().decode(AppointmentDetail.self,from:Data((row["detail_json"] as! String).utf8)),choice=TaskDraftAppointmentChoice(detail:detail,business:row["business"] as! Int,id:row["id"] as! Int)
        try expect((choice != nil)==row["valid"] as! Bool,"Appointment independent identity or unsupported eligibility rule: \(row["name"]!)")
        if let choice {let title=try JSONDecoder().decode(String?.self,from:Data((row["title_json"] as! String).utf8));try expect(choice.title.map({Data($0.utf8)})==title.map({Data($0.utf8)}) && choice.startAt==detail.appointment.start_at && choice.endAt==detail.appointment.end_at && choice.status==detail.appointment.status,"Appointment readonly title/time/status normalized/defaulted")}
    }
    let source=APIReadRepository(transport:FixtureTransport(directory:directory)),context=TaskDraftContext(business:101,epoch:1),auth=SyntheticTaskCreateGrant(business:101,actor:9001,create:true).authorization(for:context)!,choice=TaskDraftAppointmentChoice(detail:try await source.appointment(business:101,id:501),business:101,id:501)!,foreign=TaskDraftAppointmentChoice(detail:try await source.appointment(business:202,id:601),business:202,id:601)!,client=TaskDraftClientChoice(profile:try await source.clientProfile(business:101,id:701),business:101,id:701)
    // A different separately read Client is valid: serializer proves same Business only.
    let selectedClient=client!
    func editor(_ selected:TaskDraftAppointmentChoice?)->TaskDraftSession {
        var s=TaskDraftSession();s.bind(context);_=s.open(expected:context);let q=s.selection!;s.update(.title,value:"  Manual visit task\n",expected:q);s.update(.description,value:"  Exact raw notes\n",expected:q);s.chooseDue(.setDate,expected:q);s.update(.dueAt,value:"2026-11-02T09:30:00+05:00",expected:q);s.chooseReminder(.setDate,expected:q);s.update(.reminderAt,value:"2026-11-01T14:00:00Z",expected:q);s.chooseClient(selectedClient,expected:q);s.chooseAppointment(selected,expected:q);return s
    }
    var draft=editor(choice);let before=draft.values;draft.chooseAppointment(foreign,expected:draft.selection!);try expect(draft.values==before,"Foreign Appointment overwrote draft")
    draft.chooseAppointment(nil,expected:draft.selection!);try expect(draft.values.appointment==nil && draft.values.client==before.client && draft.values.title==before.title && draft.values.description==before.description && draft.values.dueDate==before.dueDate && draft.values.reminderDate==before.reminderDate,"Removing unsent Appointment altered Client/raw fields")
    for row in catalog["receipt_cases"] as! [[String:Any]] {
        var s=editor(row["selected"] is NSNull ? nil:choice);let q=s.selection!;try expect(s.prepare(expected:q),"Appointment cannot review valid independent relation");let review=s.review!;var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:review,authorization:auth)!,body=a.preparedBody()!,payload=try JSONSerialization.jsonObject(with:body) as! [String:Any]
        try expect(payload["appointment_id"]==nil && payload["appointment"] as? Int==review.preview.appointmentID && payload["client"] as? Int==selectedClient.id && payload["due_at"] as? String==review.preview.dueAt && payload["reminder_at"] as? String==review.preview.reminderAt,"Generic Appointment FK renamed/defaulted or Client/dates inferred")
        try expect(a.preparedBody()==body && a.review.values==review.values,"Prepared relation/raw body not immutable/deterministic")
        let read=TaskCreateAppointmentRead.decode(Data((row["body_json"] as! String).utf8)),kind=row["kind"] as! String,expected:TaskCreateAppointmentRead=kind=="appointment" ? .appointment(row["id"] as! Int):kind=="notSet" ? .notSet:.unknown
        try expect(read==expected,"Generic Appointment receipt aliased/coerced from bounded GET: \(row["name"]!)")
        let v=review.preview,task=WorkTask(id:88001,title:v.title,status:"open",priority:v.priority,due_at:v.dueAt,business:101,updated_at:"2026-10-30T12:00:00Z",description:v.description,created_by:9001,created_at:"2026-10-30T12:00:00Z")
        ledger.complete(a,outcome:.response(status:row["status"] as! Int,task:task,reminderAt:v.reminderAt,clientRead:.client(selectedClient.id),appointmentRead:read));let record=ledger.visible(auth)!,yes=row["accepted"] as! Bool
        try expect((record.phase == .confirmed)==yes && record.appointmentID==(yes ? v.appointmentID:nil),"Unverified Appointment became synthetic receipt or unselected FK promoted")
        if !yes {try expect(ledger.blocked(context) && !ledger.acknowledge(auth) && ledger.begin(review:review,authorization:auth)==nil && record.attempt.preparedBody()==body && record.attempt.review.values==review.values,"Unknown Appointment lost input/attempt/body or allowed replay")}
    }
    var fake=editor(choice);_=fake.prepare(expected:fake.selection!);var ledger=TaskCreateAttemptLedger();let a=ledger.begin(review:fake.review!,authorization:auth)!;ledger.complete(a,outcome:try await FixtureTaskCreatePort(directory:directory).execute(a));try expect(ledger.visible(auth)?.phase == .confirmed && ledger.visible(auth)?.appointmentID==501 && ledger.visible(auth)?.clientID==selectedClient.id,"Explicit fake port did not return independent generic FKs")
    for row in catalog["read_feedback_cases"] as! [[String:String]] {
        let states:[String:ReadFailure]=["denied":.denied,"not_found":.notFound,"unavailable":.unavailable,"invalid_payload":.invalidPayload,"invalid_context":.invalidContext]
        try expect(TaskAppointmentReadFeedback.copyKey(states[row["problem"]!]!)==row["copy_key"],"Appointment reader feedback collapsed existing denied/notFound or exposed unsafe error")
    }
    return count
}
