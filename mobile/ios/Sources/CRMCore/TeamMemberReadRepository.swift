import Foundation

public protocol TeamMemberReadRepository:Sendable {func member(business:Int,id:Int) async throws -> TeamMemberReadSource}
public struct APITeamMemberReadRepository:TeamMemberReadRepository {
    private let transport:any ReadTransport
    public init(transport:any ReadTransport) {self.transport=transport}
    public func member(business:Int,id:Int) async throws -> TeamMemberReadSource {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max) else {throw ReadFailure.invalidContext}
        let r=try await transport.get(ReadRequest(path:"/api/team/members/\(id)/"))
        guard r.status==200 else {throw r.status==403 ? ReadFailure.denied:r.status==404 ? .notFound:.unavailable}
        guard let s=TeamMemberReadSource.decode(r.data,business:business,id:id) else {throw ReadFailure.invalidPayload};return s
    }
}
