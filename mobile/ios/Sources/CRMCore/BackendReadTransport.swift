import Foundation

// HTTP execution seam. Session/credential policy is supplied independently by its owner.
public protocol NativeReadHTTPExchange: Sendable {
    func execute(_ request: URLRequest) async throws -> ReadResponse
}
public struct BackendReadTransport: ReadTransport {
    private let builder: NativeRequestBuilder
    private let exchange: any NativeReadHTTPExchange
    public init(builder: NativeRequestBuilder,exchange: any NativeReadHTTPExchange) {self.builder=builder;self.exchange=exchange}
    public func get(_ request: ReadRequest) async throws -> ReadResponse {
        try Task.checkCancellation()
        let descriptor=try builder.request(for:request)
        let response=try await exchange.execute(descriptor)
        try Task.checkCancellation()
        return response
    }
}
// No default session, credential store, retry, fallback or implicit configuration.
// The caller must supply its approved session; local checks inject in-memory exchange.
public struct URLSessionReadExchange: NativeReadHTTPExchange {
    private let session: URLSession
    public init(session: URLSession) {self.session=session}
    public func execute(_ request: URLRequest) async throws -> ReadResponse {
        guard request.httpMethod == "GET",request.httpBody == nil,request.httpBodyStream == nil else {throw RequestConfigurationFailure.invalidPath}
        try Task.checkCancellation()
        let (data,response)=try await session.data(for:request)
        try Task.checkCancellation()
        guard let response=response as? HTTPURLResponse else {throw ReadFailure.unavailable}
        return ReadResponse(status:response.statusCode,data:data)
    }
}
