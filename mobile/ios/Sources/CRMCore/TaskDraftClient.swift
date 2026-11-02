import Foundation

// An unsent local relation choice from an independently scoped profile, never a CREATE grant.
public struct TaskDraftClientChoice:Equatable,Sendable {
    public let business:Int;public let id:Int;public let title:String?
    public init?(profile:ClientProfile,business:Int,id:Int) {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max),profile.valid(for:business,id:id) else {return nil}
        self.business=business;self.id=id;title=profile.client.title
    }
    public func valid(for business:Int)->Bool {business>0 && self.business==business && id>0 && id<=Int(Int32.max)}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.business==rhs.business && lhs.id==rhs.id && lhs.title.map({Data($0.utf8)})==rhs.title.map({Data($0.utf8)})}
}
// Selected existing generic TaskSerializer.client only. Bounded GET client_id is not this evidence.
public enum TaskCreateClientRead:Equatable,Sendable {
    case unknown,notSet,client(Int)
    public static func decode(_ data:Data)->Self {
        guard let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let value=o["client"] else {return .unknown}
        if value is NSNull {return .notSet}
        guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return .unknown}
        return .client(Int(n.int64Value))
    }
    public func matches(_ selected:Int?)->Bool {guard let selected else {return true};return selected>0 && self == .client(selected)}
}
