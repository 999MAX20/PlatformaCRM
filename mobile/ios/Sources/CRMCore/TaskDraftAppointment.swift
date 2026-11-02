import Foundation

// Explicit date-only read input, no clock or Task deadline default.
public enum TaskAppointmentDay {
    public static func valid(_ raw:String)->Bool {
        let b=Array(raw.utf8)
        return b.count==10 && b[4]==45 && b[7]==45 && b.enumerated().allSatisfy({i,v in i==4 || i==7 || (48...57).contains(v)}) && !raw.hasPrefix("0000") && Day.isValid(raw)
    }
}
// Read reference for a manual Task, never built-in follow-up/booking/lifecycle authority.
public struct TaskDraftAppointmentChoice:Equatable,Sendable {
    public let business:Int;public let id:Int;public let title:String?;public let startAt:String?;public let endAt:String?;public let status:String
    public init?(detail:AppointmentDetail,business:Int,id:Int) {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max),detail.business==business,detail.appointment.id==id else {return nil}
        self.business=business;self.id=id;title=detail.appointment.title;startAt=detail.appointment.start_at;endAt=detail.appointment.end_at;status=detail.appointment.status
    }
    public func valid(for business:Int)->Bool {business>0 && self.business==business && id>0 && id<=Int(Int32.max)}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.business==rhs.business && lhs.id==rhs.id && lhs.title.map({Data($0.utf8)})==rhs.title.map({Data($0.utf8)}) && lhs.startAt.map({Data($0.utf8)})==rhs.startAt.map({Data($0.utf8)}) && lhs.endAt.map({Data($0.utf8)})==rhs.endAt.map({Data($0.utf8)}) && lhs.status.utf8.elementsEqual(rhs.status.utf8)}
}
// Existing generic TaskSerializer.appointment; GET details.appointment_id is not evidence.
public enum TaskCreateAppointmentRead:Equatable,Sendable {
    case unknown,notSet,appointment(Int)
    public static func decode(_ data:Data)->Self {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let value=o["appointment"] else {return .unknown}
        if value is NSNull {return .notSet}
        guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return .unknown}
        return .appointment(Int(n.int64Value))
    }
    public func matches(_ selected:Int?)->Bool {guard let selected else {return true};return selected>0 && self == .appointment(selected)}
}

// Existing safe presentation categories only, no backend envelope or raw provider errors.
public enum TaskAppointmentReadFeedback {
    public static func copyKey(_ failure:ReadFailure)->String {
        switch failure {case .denied:return "denied";case .notFound:return "notFound";default:return "unavailable"}
    }
}
