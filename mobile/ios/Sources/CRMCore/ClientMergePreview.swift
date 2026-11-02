import Foundation

// Existing client_snapshot shape, not bounded ClientProfile or a permission.
public struct ClientMergeSnapshot: Decodable, Equatable, Sendable {
    public let id: Int
    public let full_name: String
    public let phone: String
    public let email: String
    public let whatsapp_id: String
    public let telegram_id: String
    public let instagram_id: String
    public let source: String
    public let is_archived: Bool
    public static func ==(lhs: Self,rhs: Self) -> Bool {
        lhs.id == rhs.id && lhs.is_archived == rhs.is_archived &&
        SourceTextIdentity.same(lhs.full_name,rhs.full_name) && SourceTextIdentity.same(lhs.phone,rhs.phone) &&
        SourceTextIdentity.same(lhs.email,rhs.email) && SourceTextIdentity.same(lhs.whatsapp_id,rhs.whatsapp_id) &&
        SourceTextIdentity.same(lhs.telegram_id,rhs.telegram_id) && SourceTextIdentity.same(lhs.instagram_id,rhs.instagram_id) && SourceTextIdentity.same(lhs.source,rhs.source)
    }
}
public struct ClientMergeTransferCounts: Decodable, Equatable, Sendable {
    public static let fields=["leads","appointments","conversations","bot_conversations","tasks","deals","notes","activity_events","analytics_events","notifications","tags","attachments","custom_field_values"]
    public let provided: [String:Int]
    public init(from decoder: any Decoder) throws {
        let values=try [String:Int](from:decoder)
        guard Set(values.keys) == Set(Self.fields),values.values.allSatisfy({$0 >= 0}) else {throw ReadFailure.invalidPayload}
        provided=values
    }
}
// Exact existing merge-dry-run response. No operation receipt, version or outcome.
public struct ClientMergePreview: Decodable, Equatable, Sendable {
    public let target_client_id: Int
    public let duplicate: ClientMergeSnapshot
    public let transferred: ClientMergeTransferCounts
    public let will_delete_duplicate: Bool
    public let policy: String
    public var valid: Bool {target_client_id > 0 && duplicate.id > 0 && target_client_id != duplicate.id && !will_delete_duplicate && policy == "archive_duplicate_after_transfer"}
    public func matches(_ context: ClientMergePreviewContext,duplicate id: Int) -> Bool {context.valid && valid && target_client_id == context.target && duplicate.id == id}
    public static func decode(_ data: Data) throws -> Self {
        let value=try JSONDecoder().decode(Self.self,from:data);guard value.valid else {throw ReadFailure.invalidPayload};return value
    }
}
// Synthetic local source/owner context outside the server response, never a wire DTO/grant.
public struct ClientMergePreviewContext: Equatable, Sendable {
    public let business: Int
    public let target: Int
    public let epoch: Int
    public let readRevision: Int
    public init(business:Int,target:Int,epoch:Int,readRevision:Int) {self.business=business;self.target=target;self.epoch=epoch;self.readRevision=readRevision}
    public var valid: Bool {business > 0 && target > 0 && epoch > 0 && readRevision > 0}
}
public protocol SyntheticClientMergePreviewSource: Sendable {
    func candidates(for context: ClientMergePreviewContext) async throws -> [ClientMergeSnapshot]?
    func preview(for context: ClientMergePreviewContext,duplicate: Int) async throws -> ClientMergePreview?
}
public struct FixtureClientMergePreviewSource: SyntheticClientMergePreviewSource {
    private struct Group: Decodable, Sendable {let business: Int;let target: Int;let previews: [ClientMergePreview]}
    private struct Catalog: Decodable, Sendable {let fixture_only: Bool;let catalogs: [Group]}
    private let catalog: Catalog?
    public init(directory: URL) {catalog=(try? Data(contentsOf:directory.appendingPathComponent("client-merge-preview.json"))).flatMap {try? JSONDecoder().decode(Catalog.self,from:$0)}}
    private func group(_ context: ClientMergePreviewContext) -> Group? {
        guard context.valid,let catalog,catalog.fixture_only else {return nil}
        let groups=catalog.catalogs.filter {$0.business == context.business && $0.target == context.target}
        guard groups.count == 1,let group=groups.first,group.previews.allSatisfy({$0.valid && $0.target_client_id == context.target}),Set(group.previews.map { $0.duplicate.id }).count == group.previews.count else {return nil}
        return group
    }
    public func candidates(for context: ClientMergePreviewContext) async throws -> [ClientMergeSnapshot]? {group(context)?.previews.map(\.duplicate)}
    public func preview(for context: ClientMergePreviewContext,duplicate: Int) async throws -> ClientMergePreview? {group(context)?.previews.first {$0.matches(context,duplicate:duplicate)}}
}
