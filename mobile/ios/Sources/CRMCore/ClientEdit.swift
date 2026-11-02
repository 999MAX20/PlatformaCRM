import Foundation

// Four existing client fields only. This is local state, not a PATCH payload.
public struct ClientEditValues: Equatable, Sendable {
    public var fullName: String;public var phone: String;public var email: String;public var source: String
    public init(fullName: String,phone: String,email: String,source: String) {self.fullName=fullName;self.phone=phone;self.email=email;self.source=source}
    public static let fields: [ClientDraftField]=[.fullName,.phone,.email,.source]
    public func value(_ field: ClientDraftField) -> String {switch field {case .fullName:fullName;case .phone:phone;case .email:email;case .source:source;case .notes:""}}
    public var issues: [ClientDraftIssue] {
        var value=ClientDraftValues();value.fullName=fullName;value.phone=phone;value.email=email;value.source=source
        return value.issues.filter {$0.field != .notes}
    }
    public mutating func set(_ field: ClientDraftField,_ value: String) {switch field {case .fullName:fullName=value;case .phone:phone=value;case .email:email=value;case .source:source=value;case .notes:break}}
}
// Existing detail.client keys, consumed separately from display fallbacks.
// Missing/null/wrong-type is unknown, while an explicitly present "" stays "".
public struct ClientEditReadFields: Decodable, Equatable, Sendable {
    public let fullName: String?;public let phone: String?;public let email: String?;public let source: String?;public let version: String?
    private enum CodingKeys: String,CodingKey {case title,phone,email,source;case version="updated_at"}
    public init(from decoder: any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        fullName=try? c.decode(String.self,forKey:.title);phone=try? c.decode(String.self,forKey:.phone);email=try? c.decode(String.self,forKey:.email);source=try? c.decode(String.self,forKey:.source);version=try? c.decode(String.self,forKey:.version)
    }
    public var complete: ClientEditOrigin? {
        guard let fullName,let phone,let email,let source,ClientDraftValues.sources.contains(source),let version,!version.isEmpty else {return nil}
        return ClientEditOrigin(values:ClientEditValues(fullName:fullName,phone:phone,email:email,source:source),version:version)
    }
}
public struct ClientEditOrigin: Equatable, Sendable {public let values: ClientEditValues;public let version: String}
public protocol ClientEditOriginProvider: Sendable {func origin(for profile: ClientProfile) async -> ClientEditOrigin?}
// Explicit DEBUG fixture trust only. Opaque/current read projections do not
// become editable merely because their display strings happen to be nonempty.
public struct FixtureClientEditOriginProvider: ClientEditOriginProvider {
    private let directory: URL
    public init(directory: URL) {self.directory=directory}
    public func origin(for profile: ClientProfile) async -> ClientEditOrigin? {
        guard profile.valid(for:profile.business,id:profile.client.id),[101,202].contains(profile.business) else {return nil}
        guard let data=try? Data(contentsOf:directory.appendingPathComponent("client-\(profile.business)-\(profile.client.id).json")),let reference=try? JSONDecoder().decode(ClientProfile.self,from:data),reference.valid(for:profile.business,id:profile.client.id),reference.editReadFields==profile.editReadFields else {return nil}
        return reference.editReadFields.complete
    }
}
public struct ClientEditContext: Equatable, Sendable {
    public let business: Int;public let client: Int;public let epoch: Int
    public init(business: Int,client: Int,epoch: Int) {self.business=business;self.client=client;self.epoch=epoch}
    public var valid: Bool {business>0 && client>0 && epoch>0}
}
public struct ClientEditSelection: Equatable, Sendable {public let context: ClientEditContext;public let generation: Int}
public struct ClientEditReview: Equatable, Sendable {
    public let selection: ClientEditSelection;public let original: ClientEditValues;public let values: ClientEditValues
    public var changed: [ClientDraftField] {ClientEditValues.fields.filter {original.value($0) != values.value($0)}}
}
public struct ClientEditSession: Sendable {
    private struct Stored: Sendable {let original: ClientEditOrigin;var values: ClientEditValues;var dirty: Bool {original.values != values}}
    public private(set) var context: ClientEditContext?
    public private(set) var selection: ClientEditSelection?
    public private(set) var origin: ClientEditOrigin?
    public private(set) var values: ClientEditValues?
    public private(set) var available=false
    public private(set) var needsReset=false
    public private(set) var phase: ClientDraftPhase = .closed
    public private(set) var issues: [ClientDraftIssue]=[]
    public private(set) var review: ClientEditReview?
    private var ownerBusiness: Int?,ownerEpoch: Int?,generation=0
    private var stored: [Int:Stored]=[:]
    private var fresh: ClientEditOrigin?
    public init() {}
    public var hasStoredChanges: Bool {guard let context else {return false};return stored[context.client]?.dirty == true}
    private mutating func stash() {if let context,let origin,let values {stored[context.client]=Stored(original:origin,values:values)}}
    private mutating func hide() {generation += 1;selection=nil;origin=nil;values=nil;available=false;needsReset=false;phase = .closed;issues=[];review=nil;fresh=nil}
    public mutating func begin(_ next: ClientEditContext?) {
        stash();hide()
        guard let next,next.valid else {context=nil;stored=[:];ownerBusiness=nil;ownerEpoch=nil;return}
        if ownerBusiness != next.business || ownerEpoch != next.epoch {stored=[:]}
        ownerBusiness=next.business;ownerEpoch=next.epoch;context=next
    }
    public mutating func receive(_ next: ClientEditOrigin?,expected: ClientEditContext) {
        guard context==expected else {return};stash();hide();fresh=next
        guard let next else {needsReset=hasStoredChanges;return}
        if let previous=stored[expected.client],previous.dirty {
            guard previous.original==next else {needsReset=true;return}
            origin=next;values=previous.values
        } else {origin=next;values=next.values}
        available=true;stash()
    }
    public mutating func pause() {stash();hide();context=nil}
    @discardableResult public mutating func open(expected: ClientEditContext) -> Bool {
        guard context==expected,available,origin != nil,values != nil else {return false}
        generation += 1;selection=ClientEditSelection(context:expected,generation:generation);phase = .editing;issues=[];review=nil;return true
    }
    public mutating func update(_ field: ClientDraftField,value: String,expected: ClientEditSelection) {
        guard selection==expected,available,phase == .editing,ClientEditValues.fields.contains(field) else {return}
        values?.set(field,value);issues.removeAll {$0.field==field};stash()
    }
    @discardableResult public mutating func prepare(expected: ClientEditSelection) -> Bool {
        guard selection==expected,available,phase == .editing,let origin,let values else {return false}
        issues=values.issues;guard issues.isEmpty else {return false}
        review=ClientEditReview(selection:expected,original:origin.values,values:values);phase = .review;return true
    }
    public mutating func back(expected: ClientEditSelection) {
        guard selection==expected else {return}
        if phase == .review {phase = .editing;review=nil} else {close(expected:expected)}
    }
    public mutating func close(expected: ClientEditSelection) {
        guard selection==expected else {return};stash();generation += 1;selection=nil;phase = .closed;review=nil
    }
    public mutating func cancel(expected: ClientEditSelection) {
        guard selection==expected,let origin else {return};values=origin.values;issues=[];stash();close(expected:expected)
    }
    public mutating func discardStored(expected: ClientEditContext) {
        guard context==expected else {return};stored.removeValue(forKey:expected.client);generation += 1;selection=nil;phase = .closed;review=nil;issues=[];needsReset=false
        origin=fresh;values=fresh?.values;available=fresh != nil;stash()
    }
}
