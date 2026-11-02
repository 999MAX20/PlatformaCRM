import Foundation

// Exact existing generic check-duplicates response, not bounded ClientProfile or a grant.
public struct ClientDuplicateRow: Decodable, Equatable, Sendable {
    public let id: Int
    public let full_name: String
    public let phone: String
    public let email: String
    public let matched_fields: [String]
    public static func ==(lhs: Self, rhs: Self) -> Bool {
        lhs.id == rhs.id && SourceTextIdentity.same(lhs.full_name,rhs.full_name) &&
        SourceTextIdentity.same(lhs.phone,rhs.phone) && SourceTextIdentity.same(lhs.email,rhs.email) && lhs.matched_fields == rhs.matched_fields
    }
    public var valid: Bool {
        let known: Set<String> = ["phone","email","whatsapp_id","telegram_id","instagram_id"]
        return id > 0 && Set(matched_fields).count == matched_fields.count && matched_fields.allSatisfy {known.contains($0)}
    }
}
public struct ClientDuplicateResponse: Decodable, Equatable, Sendable {
    public let duplicates: [ClientDuplicateRow]
    public var valid: Bool {duplicates.allSatisfy(\.valid) && Set(duplicates.map(\.id)).count == duplicates.count}
    public static func decode(_ data: Data) throws -> Self {
        let value = try JSONDecoder().decode(Self.self,from:data)
        guard value.valid else {throw ReadFailure.invalidPayload};return value
    }
}
// Local fixture lookup context only: never serialized as an API body or inferred permission.
public struct ClientDuplicatePreviewInput: Equatable, Sendable {
    public let context: ClientDraftContext
    public let phone: String
    public let email: String
    public init(context: ClientDraftContext,phone: String,email: String) {self.context=context;self.phone=phone;self.email=email}
    public static func ==(lhs: Self,rhs: Self) -> Bool {
        lhs.context == rhs.context && SourceTextIdentity.same(lhs.phone,rhs.phone) && SourceTextIdentity.same(lhs.email,rhs.email)
    }
}
public protocol SyntheticClientDuplicatePreviewSource: Sendable {
    func preview(for input: ClientDuplicatePreviewInput) async throws -> ClientDuplicateResponse?
}
public struct FixtureClientDuplicatePreviewSource: SyntheticClientDuplicatePreviewSource {
    private struct Scenario: Decodable, Sendable {let business: Int;let phone: String;let email: String;let response: ClientDuplicateResponse}
    private struct Catalog: Decodable, Sendable {let fixture_only: Bool;let scenarios: [Scenario]}
    private let catalog: Catalog?
    public init(directory: URL) {
        catalog = (try? Data(contentsOf:directory.appendingPathComponent("client-duplicate-preview.json"))).flatMap {try? JSONDecoder().decode(Catalog.self,from:$0)}
    }
    public func preview(for input: ClientDuplicatePreviewInput) async throws -> ClientDuplicateResponse? {
        guard input.context.valid,let catalog,catalog.fixture_only else {return nil}
        let matches=catalog.scenarios.filter {$0.business == input.context.business && SourceTextIdentity.same($0.phone,input.phone) && SourceTextIdentity.same($0.email,input.email)}
        guard matches.count == 1,let result=matches.first?.response,result.valid else {return nil}
        return result
    }
}
