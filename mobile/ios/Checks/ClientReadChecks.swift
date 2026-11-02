import Foundation
import CRMCore

func runClientReadChecks(directory: URL) async throws -> Int {
    var count = 0
    func expect(_ value: Bool, _ message: String) throws {
        guard value else { throw CheckFailure(message: message) }; count += 1
    }
    let transport = RecordingTransport(FixtureTransport(directory: directory))
    let repository = APIReadRepository(transport: transport)
    let page = try await repository.clients(business: 101)
    try expect(page.business == 101 && page.items.map(\.id) == [701, 702], "Client fixture route/projection changed")
    let requests = await transport.requests
    try expect(requests == [ReadRequest(path: "/api/mobile/v1/clients/", query: ["business": "101", "limit": "50"])], "Client read invented route or query")
    try expect(page.items[1].phone == nil && page.items[1].email == nil, "Null client contacts changed")
    let other = try await repository.clients(business: 202)
    try expect(other.business == 202 && other.items.map(\.id) == [801], "Client Business fixture was mixed")
    do { _ = try await repository.clients(business: 0); throw CheckFailure(message: "Invalid Client Business was requested") }
    catch let error as ReadFailure { try expect(error == .invalidContext, "Wrong Client scope error") }
    let afterInvalid = await transport.requests
    try expect(afterInvalid.count == 2, "Invalid Client scope reached transport")
    let denied = APIReadRepository(transport: FixedTransport(response: ReadResponse(status: 403, data: Data())))
    do { _ = try await denied.clients(business: 101); throw CheckFailure(message: "Denied Client read was accepted") }
    catch let error as ReadFailure { try expect(error == .denied, "Wrong Client denied error") }
    return count
}
