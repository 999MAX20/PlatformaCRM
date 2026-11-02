import Foundation

public enum NativeConnectionConfigurationFailure: Error, Equatable, Sendable {case unconfigured,unexpectedKey}
// Explicit public inputs only. Never reads env/files/credentials or chooses defaults.
public struct NativeConnectionConfiguration: Sendable {
    public let origin: URL
    public let timeoutMilliseconds: Int64
    public init(publicValues: [String:String]) throws {
        let keys:Set<String>=["CRM_API_ORIGIN","CRM_READ_TIMEOUT_SECONDS"]
        guard Set(publicValues.keys).isSubset(of:keys) else {throw NativeConnectionConfigurationFailure.unexpectedKey}
        let rawOrigin=publicValues["CRM_API_ORIGIN"]?.trimmingCharacters(in:.whitespacesAndNewlines) ?? ""
        let rawTimeout=publicValues["CRM_READ_TIMEOUT_SECONDS"]?.trimmingCharacters(in:.whitespacesAndNewlines) ?? ""
        guard !rawOrigin.isEmpty,!rawTimeout.isEmpty else {throw NativeConnectionConfigurationFailure.unconfigured}
        guard let origin=URL(string:rawOrigin) else {throw RequestConfigurationFailure.invalidOrigin}
        guard rawTimeout.range(of:#"^[0-9]+(?:\.[0-9]{1,3})?$"#,options:.regularExpression) != nil else {throw RequestConfigurationFailure.invalidTimeout}
        let parts=rawTimeout.split(separator:".",omittingEmptySubsequences:false)
        guard let seconds=Int64(parts[0]) else {throw RequestConfigurationFailure.invalidTimeout}
        let fraction=parts.count == 2 ? String(parts[1]):""
        guard let millis=Int64(fraction+String(repeating:"0",count:3-fraction.count)) else {throw RequestConfigurationFailure.invalidTimeout}
        let product=seconds.multipliedReportingOverflow(by:1000),sum=product.partialValue.addingReportingOverflow(millis)
        guard !product.overflow,!sum.overflow,sum.partialValue > 0 else {throw RequestConfigurationFailure.invalidTimeout}
        _ = try NativeRequestBuilder(origin:origin,timeout:TimeInterval(sum.partialValue)/1000)
        self.origin=origin;timeoutMilliseconds=sum.partialValue
    }
    public func requestBuilder() throws -> NativeRequestBuilder {try NativeRequestBuilder(origin:origin,timeout:TimeInterval(timeoutMilliseconds)/1000)}
}
