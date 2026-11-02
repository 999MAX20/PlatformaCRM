import Foundation

// Existing detail endpoints; kind and Business are local request context, never new wire fields.
public enum AppointmentReferenceKind:String,CaseIterable,Sendable {case service,resource
    public func request(id:Int)->ReadRequest? {guard id>0,id<=Int(Int32.max) else {return nil};return ReadRequest(path:"/api/\(self == .service ? "services":"resources")/\(id)/")}
}
public struct AppointmentReferenceDetail:Equatable,Sendable {
    public let id:Int;public let business:Int;public let name:String;public let isActive:Bool?;public let resourceType:String?
    private struct Fields:Decodable {
        let id:Int;let business:Int;let name:String;let isActive:Bool?;let resourceType:String?
        private enum CodingKeys:String,CodingKey {case id,business,name,is_active,resource_type}
        init(from decoder:any Decoder) throws {
            let c=try decoder.container(keyedBy:CodingKeys.self);id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);name=try c.decode(String.self,forKey:.name)
            isActive=try? c.decode(Bool.self,forKey:.is_active);resourceType=try? c.decode(String.self,forKey:.resource_type)
        }
    }
    public static func decode(_ data:Data,kind:AppointmentReferenceKind)->Self? {
        guard let fields=try? JSONDecoder().decode(Fields.self,from:data),let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {return nil}
        func integer(_ key:String)->Int? {guard let n=o[key] as? NSNumber,["q","i","s","l","Q","I","S","L"].contains(String(cString:n.objCType)),n.int64Value>0,n.int64Value<=Int64(Int32.max) else {return nil};return Int(n.int64Value)}
        guard let id=integer("id"),let business=integer("business"),id==fields.id,business==fields.business else {return nil}
        return Self(id:id,business:business,name:fields.name,isActive:fields.isActive,resourceType:kind == .resource ? fields.resourceType:nil)
    }
    public func valid(for business:Int,id:Int)->Bool {business>0 && id>0 && self.business==business && self.id==id}
    public var activityCopyKey:String {isActive.map {$0 ? "referenceActive":"referenceInactive"} ?? "referenceActivityUnknown"}
    public var resourceTypeCopyKey:String {switch resourceType {case "staff":"referenceTypeStaff";case "room":"referenceTypeRoom";case "hall":"referenceTypeHall";case "box":"referenceTypeBox";case "equipment":"referenceTypeEquipment";case "other":"referenceTypeOther";default:"notAvailable"}}
    public static func ==(lhs:Self,rhs:Self)->Bool {lhs.id==rhs.id && lhs.business==rhs.business && lhs.name.utf8.elementsEqual(rhs.name.utf8) && lhs.isActive==rhs.isActive && lhs.resourceType.map({Data($0.utf8)})==rhs.resourceType.map({Data($0.utf8)})}
}
public protocol AppointmentReferenceRepository:Sendable {func reference(_ kind:AppointmentReferenceKind,business:Int,id:Int) async throws -> AppointmentReferenceDetail}
public struct APIAppointmentReferenceRepository:AppointmentReferenceRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func reference(_ kind:AppointmentReferenceKind,business:Int,id:Int) async throws -> AppointmentReferenceDetail {
        guard business>0,business<=Int(Int32.max),let request=kind.request(id:id) else {throw ReadFailure.invalidContext}
        let response=try await transport.get(request)
        switch response.status {case 200:guard let detail=AppointmentReferenceDetail.decode(response.data,kind:kind),detail.valid(for:business,id:id) else {throw ReadFailure.invalidPayload};return detail
        case 403:throw ReadFailure.denied;case 404:throw ReadFailure.notFound;default:throw ReadFailure.unavailable}
    }
}
public extension AppointmentDetail {
    func referenceID(_ kind:AppointmentReferenceKind)->Int? {let id=kind == .service ? details.service?.id:details.resource?.id;return id.flatMap {$0>0 && $0<=Int(Int32.max) ? $0:nil}}
}
