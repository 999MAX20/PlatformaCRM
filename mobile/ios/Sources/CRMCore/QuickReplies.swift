import Foundation

// Existing QuickReplyTemplateSerializer fields; no new server DTO or endpoint.
public struct QuickReplyTemplate: Decodable, Equatable, Sendable, Identifiable {
    public let id: Int
    public let business: Int
    public let title: String
    public let text: String
    public let category: String
    public let channel: String
    public let sortOrder: Int
    public let isActive: Bool
    private enum CodingKeys: String, CodingKey {case id,business,title,text,category,channel;case sortOrder="sort_order",isActive="is_active"}
}
// Existing web list accepts an array or DRF results/count/next envelope.
// Missing pagination metadata never becomes proof of a complete catalogue.
public struct QuickReplyPage: Decodable, Sendable {
    public let items: [QuickReplyTemplate]
    public let count: Int?
    public let hasNext: Bool
    public let metadataKnown: Bool
    private enum CodingKeys: String,CodingKey {case results,count,next}
    public init(from decoder: any Decoder) throws {
        if let rows=try? decoder.singleValueContainer().decode([QuickReplyTemplate].self) {items=rows;count=nil;hasNext=false;metadataKnown=false;return}
        let box=try decoder.container(keyedBy:CodingKeys.self)
        items=try box.decode([QuickReplyTemplate].self,forKey:.results);count=try box.decodeIfPresent(Int.self,forKey:.count)
        hasNext=try box.decodeIfPresent(String.self,forKey:.next) != nil;metadataKnown=count != nil && box.contains(.next)
    }
    public var partial: Bool {!metadataKnown || hasNext || (count ?? items.count)>items.count}
    public func valid(for context: QuickReplyContext) -> Bool {
        context.valid && (count == nil || count!>=items.count) && Set(items.map(\.id)).count==items.count && items.allSatisfy {
            $0.id>0 && $0.business==context.draft.context.business && $0.isActive && $0.sortOrder>=0 && ["all",context.channel].contains($0.channel) && !SourceTextTrim.pythonStrip($0.text).isEmpty
        }
    }
}
public protocol QuickReplyRepository: Sendable {func quickReplies(business: Int,channel: String) async throws -> QuickReplyPage}
// Fixture-only injection. The web route is outside the native request builder;
// no production transport, header, credential or scope mapping is added here.
public struct FixtureQuickReplyRepository: QuickReplyRepository {
    private let directory: URL
    public init(directory: URL) {self.directory=directory}
    public func quickReplies(business: Int,channel: String) async throws -> QuickReplyPage {
        guard [101,202].contains(business),QuickReplyContext.channels.contains(channel) else {throw ReadFailure.invalidContext}
        do {return try JSONDecoder().decode(QuickReplyPage.self,from:Data(contentsOf:directory.appendingPathComponent("quick-replies-\(business)-\(channel).json")))}
        catch let failure as ReadFailure {throw failure}
        catch is DecodingError {throw ReadFailure.invalidPayload}
        catch {throw ReadFailure.unavailable}
    }
}
public struct QuickReplyContext: Equatable, Sendable {
    public let draft: ReplyDraftSelection
    public let channel: String
    public init(draft: ReplyDraftSelection,channel: String) {self.draft=draft;self.channel=channel}
    public static let channels=["website","telegram","whatsapp","instagram"]
    public var valid: Bool {draft.context.valid && draft.generation>0 && Self.channels.contains(channel)}
}
public struct QuickReplySelection: Equatable, Sendable {public let context: QuickReplyContext;public let generation: Int}
public struct QuickReplyRequest: Equatable, Sendable {public let selection: QuickReplySelection;public let revision: Int}
public struct QuickReplyChoice: Equatable, Sendable, Identifiable {
    public let request: QuickReplyRequest
    public let filterRevision: Int
    public let template: QuickReplyTemplate
    public var id: Int {template.id}
}
public enum QuickReplyInsertion {
    public static func text(draft: String,template: String) -> String {
        SourceTextTrim.javascriptTrim(draft).isEmpty ? template : SourceTextTrim.javascriptTrimEnd(draft)+"\n"+template
    }
}
public struct QuickReplySession: Sendable {
    public private(set) var context: QuickReplyContext?
    public private(set) var selection: QuickReplySelection?
    public private(set) var query=""
    public private(set) var items: [QuickReplyTemplate]=[]
    public private(set) var partial=false
    public private(set) var loading=false
    public private(set) var loaded=false
    public private(set) var failure: ReadFailure?
    private var generation=0,revision=0,filterRevision=0
    private var pending: QuickReplyRequest?,accepted: QuickReplyRequest?
    public init() {}
    private var visible: [QuickReplyTemplate] {
        let needle=SourceTextTrim.javascriptTrim(query).lowercased()
        return needle.isEmpty ? items : items.filter {($0.title+" "+$0.text+" "+$0.category).lowercased().contains(needle)}
    }
    public var choices: [QuickReplyChoice] {
        guard let accepted,selection==accepted.selection,loaded,!loading,failure==nil else {return []}
        return visible.map {QuickReplyChoice(request:accepted,filterRevision:filterRevision,template:$0)}
    }
    public var showsEmpty: Bool {loaded && !loading && failure==nil && !partial && choices.isEmpty}
    private mutating func invalidate() {revision += 1;pending=nil;accepted=nil;items=[];partial=false;loading=false;loaded=false;failure=nil}
    public mutating func bind(_ next: QuickReplyContext?) {
        let next=next?.valid == true ? next : nil
        guard next != context else {return};invalidate();generation += 1;context=next;selection=nil;query="";filterRevision += 1
    }
    public mutating func open(expected: QuickReplyContext) -> QuickReplyRequest? {
        guard context==expected,expected.valid else {return nil}
        invalidate();generation += 1;let selected=QuickReplySelection(context:expected,generation:generation);selection=selected
        let request=QuickReplyRequest(selection:selected,revision:revision);pending=request;loading=true;return request
    }
    public mutating func retry(expected: QuickReplySelection) -> QuickReplyRequest? {
        guard selection==expected else {return nil};invalidate()
        let request=QuickReplyRequest(selection:expected,revision:revision);pending=request;loading=true;return request
    }
    public mutating func accept(_ page: QuickReplyPage,request: QuickReplyRequest) {
        guard pending==request,selection==request.selection else {return}
        guard page.valid(for:request.selection.context) else {fail(.invalidPayload,request:request);return}
        pending=nil;accepted=request;items=page.items;partial=page.partial;loading=false;loaded=true;failure=nil
    }
    public mutating func fail(_ failure: ReadFailure,request: QuickReplyRequest) {
        guard pending==request,selection==request.selection else {return};invalidate();self.failure=failure
    }
    public mutating func cancel(request: QuickReplyRequest) {if pending==request,selection==request.selection {invalidate()}}
    public mutating func search(_ value: String,expected: QuickReplySelection) {
        guard selection==expected,!query.utf8.elementsEqual(value.utf8) else {return};query=value;filterRevision += 1
    }
    public func resolve(_ choice: QuickReplyChoice) -> String? {choices.contains(choice) ? choice.template.text : nil}
    public mutating func close(expected: QuickReplySelection) {
        guard selection==expected else {return};invalidate();generation += 1;selection=nil
    }
}
