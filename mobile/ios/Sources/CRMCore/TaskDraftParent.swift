import Foundation

// Read reference for an optional manual Task parent; no inherited fields/lifecycle authority.
public struct TaskDraftParentChoice:Equatable,Sendable {
    public let business:Int;public let id:Int;public let title:String?;public let status:String
    public init?(detail:TaskDetails,business:Int,id:Int) {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max),detail.valid(for:business,id:id) else {return nil}
        self.business=business;self.id=id;title=detail.task.title;status=detail.task.status
    }
    public func valid(for business:Int)->Bool {business>0 && self.business==business && id>0 && id<=Int(Int32.max)}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.business==rhs.business && lhs.id==rhs.id && lhs.title.map({Data($0.utf8)})==rhs.title.map({Data($0.utf8)}) && lhs.status.utf8.elementsEqual(rhs.status.utf8)}
}
// Existing generic TaskSerializer.parent_task; Bounded Task GET is not evidence.
public enum TaskCreateParentRead:Equatable,Sendable {
    case unknown,notSet,parent(Int)
    public static func decode(_ data:Data)->Self {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let value=o["parent_task"] else {return .unknown}
        if value is NSNull {return .notSet}
        guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return .unknown}
        return .parent(Int(n.int64Value))
    }
    public func matches(_ selected:Int?)->Bool {guard let selected else {return true};return selected>0 && self == .parent(selected)}
}
