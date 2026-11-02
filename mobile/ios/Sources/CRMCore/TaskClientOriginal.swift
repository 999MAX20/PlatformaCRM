import Foundation

// Presence-aware projection of existing bounded GET task.client_id, not a wire field/grant.
public enum TaskClientOriginal:Equatable,Sendable {
    case unknown,notSet,client(Int)
    static let decoderKey=CodingUserInfoKey(rawValue:"TaskClientOriginal.rawGET")!
    public var known:Bool {switch self {case .unknown:false;case .notSet:true;case .client(let id):id>0 && id<=Int(Int32.max)}}
    public static func decode(_ data:Data)->Self {
        guard let root=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let fields=root["task"] as? [String:Any],let value=fields["client_id"] else {return .unknown}
        if value is NSNull {return .notSet}
        guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return .unknown}
        return .client(Int(n.int64Value))
    }
}
