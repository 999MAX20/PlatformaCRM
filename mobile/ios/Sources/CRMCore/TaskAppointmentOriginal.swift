import Foundation

// Presence-aware projection of existing bounded GET details.appointment_id, not a wire field/grant.
public enum TaskAppointmentOriginal:Equatable,Sendable {
    case unknown,notSet,appointment(Int)
    static let decoderKey=CodingUserInfoKey(rawValue:"TaskAppointmentOriginal.rawGET")!
    public var known:Bool {switch self {case .unknown:false;case .notSet:true;case .appointment(let id):id>0 && id<=Int(Int32.max)}}
    public static func decode(_ data:Data)->Self {
        guard let root=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],let fields=root["details"] as? [String:Any],let value=fields["appointment_id"] else {return .unknown}
        if value is NSNull {return .notSet}
        guard let n=value as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return .unknown}
        return .appointment(Int(n.int64Value))
    }
}
