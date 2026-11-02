import Foundation

public struct WorkTask: Codable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String?
    public let status: String
    public let priority: String?
    public let due_at: String?
    public let client_id: Int?
    // Optional existing TaskSerializer action fields; not present in _task_item read projection.
    public let business: Int?
    public let cancelled_at: String?
    public let cancelled_by: Int?
    public let cancel_reason: String?
    public let updated_at: String?
    public let description: String?
    public let created_by: Int?
    public let created_at: String?
    public init(id: Int,title: String?,status: String,priority: String?,due_at: String?,client_id: Int?=nil,business: Int?=nil,cancelled_at: String?=nil,cancelled_by: Int?=nil,cancel_reason: String?=nil,updated_at: String?=nil,description: String?=nil,created_by: Int?=nil,created_at: String?=nil) {
        self.id=id;self.title=title;self.status=status;self.priority=priority;self.due_at=due_at;self.client_id=client_id;self.business=business;self.cancelled_at=cancelled_at;self.cancelled_by=cancelled_by;self.cancel_reason=cancel_reason;self.updated_at=updated_at;self.description=description;self.created_by=created_by;self.created_at=created_at
    }
    public static func ==(lhs:Self,rhs:Self)->Bool {
        guard lhs.id==rhs.id,lhs.status==rhs.status,lhs.priority==rhs.priority,lhs.due_at==rhs.due_at,lhs.client_id==rhs.client_id else {return false}
        guard lhs.business==rhs.business,lhs.cancelled_at==rhs.cancelled_at,lhs.cancelled_by==rhs.cancelled_by,lhs.updated_at==rhs.updated_at,lhs.created_by==rhs.created_by,lhs.created_at==rhs.created_at else {return false}
        return SourceTextIdentity.same(lhs.title,rhs.title) && SourceTextIdentity.same(lhs.cancel_reason,rhs.cancel_reason) && SourceTextIdentity.same(lhs.description,rhs.description)
    }
    public var valid: Bool { id > 0 && (due_at == nil || Appointment.instant(due_at!) != nil) }
}
public struct TaskPage: Decodable, Sendable {
    public struct Summary: Decodable, Sendable { public let total: Int }
    public let business: Int
    public let items: [WorkTask]
    public let summary: Summary
    public func valid(for scope: Int) -> Bool {
        scope > 0 && business == scope && summary.total >= items.count && items.allSatisfy(\.valid) && Set(items.map(\.id)).count == items.count
    }
}
// One existing comment entity, with optional action fields absent from the bounded mobile read.
public struct TaskComment: Decodable, Identifiable, Equatable, Sendable {
    public let id: Int
    public let text: String?
    public let created_at: String?
    public let task: Int?
    public let author: Int?
    public let author_name: String?
    public let author_email: String?
    public let authorRead: MobileUserRead
    public init(id: Int,text: String?,created_at: String?,task: Int?=nil,author: Int?=nil,author_name: String?=nil,author_email: String?=nil,authorRead: MobileUserRead = .unknown) {
        self.id=id;self.text=text;self.created_at=created_at;self.task=task;self.author=author;self.author_name=author_name;self.author_email=author_email;self.authorRead=authorRead
    }
    public static func ==(lhs:Self,rhs:Self)->Bool {
        lhs.id==rhs.id && SourceTextIdentity.same(lhs.text,rhs.text) && lhs.created_at==rhs.created_at && lhs.task==rhs.task && lhs.author==rhs.author && lhs.author_name==rhs.author_name && lhs.author_email==rhs.author_email && lhs.authorRead==rhs.authorRead
    }
    private enum CodingKeys: String,CodingKey {case id,text,created_at,task,author,author_name,author_email}
    public init(from decoder: any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(Int.self,forKey:.id);text=try c.decodeIfPresent(String.self,forKey:.text);created_at=try c.decodeIfPresent(String.self,forKey:.created_at)
        task=try c.decodeIfPresent(Int.self,forKey:.task)
        // The mobile detail uses an author miniobject; add-comment uses its numeric FK.
        author=try? c.decode(Int.self,forKey:.author)
        authorRead=MobileUserRead.decode(c,forKey:.author)
        author_name=try c.decodeIfPresent(String.self,forKey:.author_name);author_email=try c.decodeIfPresent(String.self,forKey:.author_email)
    }
}
// Read-only source state: absent/malformed is not the same as an explicit null.
public enum TaskScheduleValue: Equatable, Sendable {
    case notSet,unknown,instant(String)
}
public struct TaskDetails: Decodable, Equatable, Sendable {
    public struct Fields: Decodable, Equatable, Sendable {
        public let description: String?;public let appointment_id: Int?
        public let appointmentRead:TaskAppointmentOriginal
        public let reminder_at: TaskScheduleValue;public let snoozed_until: TaskScheduleValue
        public let created_by: MobileUserRead;public let assignee: MobileUserRead
        public static func ==(lhs:Self,rhs:Self)->Bool {
            SourceTextIdentity.same(lhs.description,rhs.description) && lhs.appointment_id==rhs.appointment_id && lhs.appointmentRead==rhs.appointmentRead && lhs.reminder_at==rhs.reminder_at && lhs.snoozed_until==rhs.snoozed_until && lhs.created_by==rhs.created_by && lhs.assignee==rhs.assignee
        }
        private enum CodingKeys: String,CodingKey {case description,appointment_id,reminder_at,snoozed_until,created_by,assignee}
        public init(from decoder: any Decoder) throws {
            let c=try decoder.container(keyedBy:CodingKeys.self)
            description=try c.decodeIfPresent(String.self,forKey:.description);appointment_id=try c.decodeIfPresent(Int.self,forKey:.appointment_id)
            if let raw=decoder.userInfo[TaskAppointmentOriginal.decoderKey] as? TaskAppointmentOriginal {appointmentRead=raw}
            else if !c.contains(.appointment_id) {appointmentRead = .unknown}
            else if (try? c.decodeNil(forKey:.appointment_id))==true {appointmentRead = .notSet}
            else if let id=appointment_id,id>0,id<=Int(Int32.max) {appointmentRead = .appointment(id)}
            else {appointmentRead = .unknown}
            func schedule(_ key: CodingKeys) -> TaskScheduleValue {
                guard c.contains(key) else {return .unknown}
                if (try? c.decodeNil(forKey:key))==true {return .notSet}
                guard let raw=try? c.decode(String.self,forKey:key),Appointment.instant(raw) != nil else {return .unknown}
                return .instant(raw)
            }
            reminder_at=schedule(.reminder_at);snoozed_until=schedule(.snoozed_until)
            created_by=MobileUserRead.decode(c,forKey:.created_by);assignee=MobileUserRead.decode(c,forKey:.assignee)
        }
    }
    public struct Budget: Decodable, Equatable, Sendable { public let max_comments: Int }
    public let business: Int
    public let task: WorkTask
    public let details: Fields
    public let clientRead:TaskClientOriginal
    public let comments: [TaskComment]
    public let payload_budget: Budget
    private enum CodingKeys:String,CodingKey {case business,task,details,comments,payload_budget}
    private enum ClientKeys:String,CodingKey {case client_id}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        business=try c.decode(Int.self,forKey:.business);task=try c.decode(WorkTask.self,forKey:.task);details=try c.decode(Fields.self,forKey:.details);comments=try c.decode([TaskComment].self,forKey:.comments);payload_budget=try c.decode(Budget.self,forKey:.payload_budget)
        if let raw=decoder.userInfo[TaskClientOriginal.decoderKey] as? TaskClientOriginal {clientRead=raw}
        else {
            // Legacy direct fixture decoding preserves equality; transport paths use strict same-byte metadata.
            let h=try c.nestedContainer(keyedBy:ClientKeys.self,forKey:.task)
            if !h.contains(.client_id) {clientRead = .unknown}
            else if (try? h.decodeNil(forKey:.client_id))==true {clientRead = .notSet}
            else if let id=task.client_id,id>0,id<=Int(Int32.max) {clientRead = .client(id)}
            else {clientRead = .unknown}
        }
    }
    static func sourceDecoder(_ data:Data)->JSONDecoder {
        let d=JSONDecoder();d.userInfo[TaskAppointmentOriginal.decoderKey]=TaskAppointmentOriginal.decode(data);d.userInfo[TaskClientOriginal.decoderKey]=TaskClientOriginal.decode(data);return d
    }
    public static func decodeSource(_ data:Data)throws->TaskDetails {try sourceDecoder(data).decode(TaskDetails.self,from:data)}
    public var commentsCapped: Bool { comments.count == payload_budget.max_comments }
    public func valid(for scope: Int, id: Int) -> Bool {
        scope > 0 && id > 0 && business == scope && task.id == id && task.valid && payload_budget.max_comments > 0 && comments.count <= payload_budget.max_comments && comments.allSatisfy { $0.id > 0 } && Set(comments.map(\.id)).count == comments.count
    }
}
