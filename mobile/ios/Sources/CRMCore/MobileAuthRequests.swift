import Foundation

// Existing server enum. These are wire inputs, never a generated native device identity.
public enum MobileDevicePlatform: String, Codable, Sendable {case ios,android}
public struct MobileAuthDeviceInput: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let deviceID:String
    public let platform:MobileDevicePlatform
    public let appVersion:String?,buildNumber:String?,osVersion:String?,deviceModel:String?
    public init(deviceID:String,platform:MobileDevicePlatform,appVersion:String?,buildNumber:String?,osVersion:String?,deviceModel:String?) {
        self.deviceID=deviceID;self.platform=platform;self.appVersion=appVersion;self.buildNumber=buildNumber;self.osVersion=osVersion;self.deviceModel=deviceModel
    }
    public var description:String {"MobileAuthDeviceInput(redacted)"}
    public var debugDescription:String {description}
}
// Raw caller inputs are encoded exactly. Server serializer owns normalization/validation.
// No environment/credential access, storage, default Business or network execution.
public struct MobileLoginInput: Encodable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let device:MobileAuthDeviceInput
    public let email:String,password:String
    public let business:Int?
    public init(device:MobileAuthDeviceInput,email:String,password:String,business:Int?) {self.device=device;self.email=email;self.password=password;self.business=business}
    private enum Keys:String,CodingKey {case device_id,platform,email,password,business,app_version,build_number,os_version,device_model}
    public func encode(to encoder:any Encoder) throws {
        var c=encoder.container(keyedBy:Keys.self)
        try c.encode(device.deviceID,forKey:.device_id);try c.encode(device.platform,forKey:.platform)
        try c.encode(email,forKey:.email);try c.encode(password,forKey:.password);try c.encodeIfPresent(business,forKey:.business)
        try c.encodeIfPresent(device.appVersion,forKey:.app_version);try c.encodeIfPresent(device.buildNumber,forKey:.build_number)
        try c.encodeIfPresent(device.osVersion,forKey:.os_version);try c.encodeIfPresent(device.deviceModel,forKey:.device_model)
    }
    public var description:String {"MobileLoginInput(redacted)"}
    public var debugDescription:String {description}
}
public struct MobileRefreshInput: Encodable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let refresh:String
    public init(refresh:String) {self.refresh=refresh}
    public var description:String {"MobileRefreshInput(redacted)"}
    public var debugDescription:String {description}
}
public struct MobileLogoutInput: Encodable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let refresh:String?
    public init(refresh:String?) {self.refresh=refresh}
    public var description:String {"MobileLogoutInput(redacted)"}
    public var debugDescription:String {description}
}
