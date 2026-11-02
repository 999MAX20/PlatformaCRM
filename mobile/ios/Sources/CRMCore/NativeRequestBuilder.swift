import Foundation

public enum RequestConfigurationFailure: Error, Equatable, Sendable {
    case invalidOrigin, invalidPath, invalidTimeout
}
/// Pure wire-request construction. It does not open a connection or read credentials.
public struct NativeRequestBuilder: Sendable {
    private let origin: URL
    private let timeout: TimeInterval
    public init(origin: URL, timeout: TimeInterval) throws {
        guard origin.scheme?.lowercased() == "https", origin.host != nil,
              origin.user == nil, origin.password == nil, origin.query == nil, origin.fragment == nil,
              origin.path.isEmpty || origin.path == "/",
              origin.port == nil || (1...65535).contains(origin.port!) else { throw RequestConfigurationFailure.invalidOrigin }
        guard timeout.isFinite && timeout > 0 else { throw RequestConfigurationFailure.invalidTimeout }
        self.origin = origin; self.timeout = timeout
    }
    public func request(for read: ReadRequest) throws -> URLRequest {
        guard !read.path.contains("//"), read.path.range(of: "^/api/mobile/v1/[A-Za-z0-9/_-]+/$", options: .regularExpression) != nil else { throw RequestConfigurationFailure.invalidPath }
        guard var components = URLComponents(url: origin, resolvingAgainstBaseURL: false) else { throw RequestConfigurationFailure.invalidOrigin }
        components.path = read.path
        components.queryItems = read.query.isEmpty ? nil : read.query.sorted { $0.key < $1.key }.map { URLQueryItem(name: $0.key, value: $0.value) }
        components.percentEncodedQuery = components.percentEncodedQuery?.replacingOccurrences(of: "+", with: "%2B")
        guard let url = components.url else { throw RequestConfigurationFailure.invalidPath }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: timeout)
        request.httpMethod = "GET"
        request.httpShouldHandleCookies = false
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        return request
    }
}
