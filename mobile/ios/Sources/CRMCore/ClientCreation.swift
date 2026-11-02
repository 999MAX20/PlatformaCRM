import Foundation

// Fake CREATE capability, never inferred from VIEW, UPDATE or displayed person data.
public struct SyntheticClientCreateGrant: Decodable,Equatable,Sendable {
    public let business: Int;public let actor: Int;public let create: Bool
    public init(business: Int,actor: Int,create: Bool) {self.business=business;self.actor=actor;self.create=create}
    public func authorization(for context: ClientDraftContext) -> SyntheticClientCreateAuthorization? {
        guard context.valid,context.business==business,actor>0,create else {return nil}
        return SyntheticClientCreateAuthorization(context:context,actor:actor)
    }
}
public struct SyntheticClientCreateAuthorization: Equatable,Sendable {
    public let context: ClientDraftContext;public let actor: Int
    fileprivate init(context: ClientDraftContext,actor: Int) {self.context=context;self.actor=actor}
}
public struct ClientCreateAttempt: Equatable,Sendable {
    // Local RAM correlation only, not an HTTP/idempotency key or server entity version.
    public let localID: Int;public let authorization: SyntheticClientCreateAuthorization;public let review: ClientDraftReview
}
public enum SyntheticClientCreateOutcome: Sendable {case response(status: Int,client: ClientContact),rejectedWithoutWrite,unknown}
public protocol SyntheticClientCreatePort: Sendable {
    var grants: [SyntheticClientCreateGrant] {get}
    func execute(_ attempt: ClientCreateAttempt) async throws -> SyntheticClientCreateOutcome
}
public enum ClientCreateAttemptPhase: Equatable,Sendable {case pending,confirmed,rejected,unknown}
public struct ClientCreateAttemptRecord: Equatable,Sendable {public let attempt: ClientCreateAttempt;public var phase: ClientCreateAttemptPhase;public var client: ClientContact?}
public struct ClientCreateAttemptLedger: Sendable {
    public private(set) var records: [ClientCreateAttemptRecord]=[]
    // One create composer per Business; an unresolved attempt cannot be replayed via new epoch.
    private var active: [Int:Int]=[:]
    public init() {}
    public func blocked(_ context: ClientDraftContext) -> Bool {active[context.business] != nil}
    public func visible(_ authorization: SyntheticClientCreateAuthorization?) -> ClientCreateAttemptRecord? {
        guard let authorization,let index=active[authorization.context.business] else {return nil}
        let record=records[index];return record.attempt.authorization==authorization ? record:nil
    }
    public mutating func begin(review: ClientDraftReview,authorization: SyntheticClientCreateAuthorization) -> ClientCreateAttempt? {
        let context=review.selection.context
        guard context.valid,context==authorization.context,authorization.actor>0,review.values.issues.isEmpty,review.preview==review.values.preview,!blocked(context) else {return nil}
        let attempt=ClientCreateAttempt(localID:records.count+1,authorization:authorization,review:review)
        active[context.business]=records.count;records.append(ClientCreateAttemptRecord(attempt:attempt,phase:.pending));return attempt
    }
    public mutating func complete(_ attempt: ClientCreateAttempt,outcome: SyntheticClientCreateOutcome) {
        guard let index=records.firstIndex(where:{$0.attempt==attempt}),records[index].phase == .pending else {return}
        var phase: ClientCreateAttemptPhase = .unknown;var accepted: ClientContact?
        switch outcome {
        case .rejectedWithoutWrite:phase = .rejected
        case .unknown:break
        case .response(let status,let client):
            let value=attempt.review.preview
            // ClientSerializer has no actor field: actor is captured local correlation, not an echo.
            if status==201,client.id>0,client.business==attempt.authorization.context.business,client.full_name==value.fullName,client.phone==value.phone,client.email==value.email,client.source==value.source,client.notes==value.notes,Appointment.instant(client.created_at) != nil,Appointment.instant(client.updated_at) != nil {phase = .confirmed;accepted=client}
        }
        records[index].phase=phase;records[index].client=accepted
    }
    // No name/contact reread is attempt-specific recovery proof.
    @discardableResult public mutating func acknowledge(_ authorization: SyntheticClientCreateAuthorization) -> Bool {
        guard let record=visible(authorization),record.phase == .confirmed || record.phase == .rejected else {return false}
        active.removeValue(forKey:authorization.context.business);return true
    }
}
public struct FixtureClientCreatePort: SyntheticClientCreatePort {
    private struct Scenario: Decodable,Sendable {let grant: SyntheticClientCreateGrant;let outcome: String;let response: ClientContact?}
    private struct Catalog: Decodable {let fixture_only: Bool;let scenarios:[Scenario]}
    private let scenarios:[Scenario]
    public var grants:[SyntheticClientCreateGrant] {scenarios.map(\.grant)}
    public init(directory: URL) {
        if let data=try? Data(contentsOf:directory.appendingPathComponent("client-create-outcome.json")),let catalog=try? JSONDecoder().decode(Catalog.self,from:data),catalog.fixture_only {scenarios=catalog.scenarios} else {scenarios=[]}
    }
    public func execute(_ attempt:ClientCreateAttempt) async throws -> SyntheticClientCreateOutcome {
        guard let scenario=scenarios.first(where:{$0.grant.authorization(for:attempt.authorization.context)==attempt.authorization}) else {return .unknown}
        switch scenario.outcome {
        case "rejected_without_write":return .rejectedWithoutWrite
        case "response":
            guard let client=scenario.response else {return .unknown};let v=attempt.review.preview
            return .response(status:201,client:ClientContact(id:client.id,title:nil,phone:v.phone,email:v.email,business:client.business,full_name:v.fullName,source:v.source,notes:v.notes,created_at:client.created_at,updated_at:client.updated_at))
        default:return .unknown
        }
    }
}
