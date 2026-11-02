import Foundation

public enum MobileAuthContractFailure: Error, Equatable, Sendable {case invalidPayload,contextMismatch}
// Supplied descriptors only. No authorization method, default grant or role synthesis.
public struct MobilePermissionDescriptor: Decodable, Sendable {
    public let resource:String,action:String,scope:String
}
public struct MobileAuthBusiness: Decodable, Sendable {
    public let id:Int
    public let name:String,slug:String,business_type:String,city:String,timezone:String,language:String,currency:String,status:String
    public let permissions:[MobilePermissionDescriptor]
}
public struct MobileAuthDeviceReply: Decodable, Sendable {
    public let id:Int,business:Int
    public let platform:MobileDevicePlatform
    public let app_version:String,build_number:String,os_version:String,device_model:String
    public let last_seen_at:String?,revoked_at:String?
    public let created_at:String,updated_at:String
    private enum Keys:String,CodingKey {case id,business,platform,app_version,build_number,os_version,device_model,last_seen_at,revoked_at,created_at,updated_at}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:Keys.self)
        id=try c.decode(Int.self,forKey:.id);business=try c.decode(Int.self,forKey:.business);platform=try c.decode(MobileDevicePlatform.self,forKey:.platform)
        app_version=try c.decode(String.self,forKey:.app_version);build_number=try c.decode(String.self,forKey:.build_number)
        os_version=try c.decode(String.self,forKey:.os_version);device_model=try c.decode(String.self,forKey:.device_model)
        last_seen_at=try c.decode(String?.self,forKey:.last_seen_at);revoked_at=try c.decode(String?.self,forKey:.revoked_at)
        created_at=try c.decode(String.self,forKey:.created_at);updated_at=try c.decode(String.self,forKey:.updated_at)
    }
}
// Opaque response text only: never parsed into expiry, principal or permission.
public struct MobileTokenReply: Decodable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let access:String,refresh:String,token_type:String
    private enum Keys:String,CodingKey {case access,refresh,token_type}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:Keys.self)
        access=try c.decode(String.self,forKey:.access);refresh=try c.decode(String.self,forKey:.refresh);token_type=try c.decode(String.self,forKey:.token_type)
        guard !access.isEmpty,!refresh.isEmpty,SourceTextIdentity.same(token_type,"Bearer") else {throw MobileAuthContractFailure.invalidPayload}
    }
    public var description:String {"MobileTokenReply(redacted)"}
    public var debugDescription:String {description}
}
public struct MobileLoginReply: Decodable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let tokens:MobileTokenReply
    public let business:MobileAuthBusiness
    public let device:MobileAuthDeviceReply
    private enum Keys:String,CodingKey {case business,device}
    public init(from decoder:any Decoder) throws {
        tokens=try MobileTokenReply(from:decoder);let c=try decoder.container(keyedBy:Keys.self)
        business=try c.decode(MobileAuthBusiness.self,forKey:.business);device=try c.decode(MobileAuthDeviceReply.self,forKey:.device)
        guard business.id>0,device.id>0,device.business==business.id else {throw MobileAuthContractFailure.invalidPayload}
    }
    public var description:String {"MobileLoginReply(redacted)"}
    public var debugDescription:String {description}
}
public struct MobileLogoutReply: Decodable, Sendable {
    public let ok:Bool
}
public enum MobileAuthJSON {
    private static func decode<T:Decodable>(_ type:T.Type,_ data:Data) throws -> T {
        do {return try JSONDecoder().decode(type,from:data)} catch {throw MobileAuthContractFailure.invalidPayload}
    }
    public static func loginResponse(_ data:Data,for input:MobileLoginInput) throws -> MobileLoginReply {
        let reply=try decode(MobileLoginReply.self,data)
        guard reply.device.platform==input.device.platform,input.business==nil || input.business==reply.business.id else {throw MobileAuthContractFailure.contextMismatch}
        return reply
    }
    public static func refreshResponse(_ data:Data) throws -> MobileTokenReply {try decode(MobileTokenReply.self,data)}
    public static func logoutResponse(_ data:Data) throws -> MobileLogoutReply {
        let reply=try decode(MobileLogoutReply.self,data);guard reply.ok else {throw MobileAuthContractFailure.invalidPayload};return reply
    }
}
