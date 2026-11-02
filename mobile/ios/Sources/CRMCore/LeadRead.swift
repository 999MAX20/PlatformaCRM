import Foundation

// Exact bounded projection of existing mobile _lead_item. No generic LeadSerializer aliases.
public struct LeadReadItem:Decodable,Equatable,Sendable {
    public struct Client:Decodable,Equatable,Sendable {public let id:Int;public let name:String;public let phone:String;public let email:String}
    public let id:Int
    public let client_id:Int
    public let title:String
    public let client:Client
    public let status:String
    public let source:String
    public let message:String
    public let created_at:String
    public var valid:Bool {id>0 && id<=Int(Int32.max) && client_id>0 && client_id<=Int(Int32.max) && client.id==client_id}
}
public struct LeadReadPage:Decodable,Sendable {
    public struct Summary:Decodable,Sendable {public let total:Int}
    public let business:Int
    public let limit:Int
    public let summary:Summary
    public let items:[LeadReadItem]
    public func valid(for business:Int)->Bool {business>0 && self.business==business && limit==50 && summary.total>=items.count && summary.total<=Int(Int32.max) && items.count<=limit && items.allSatisfy(\.valid) && Set(items.map(\.id)).count==items.count}
}
public struct LeadReadDetail:Decodable,Equatable,Sendable {
    public struct Fields:Decodable,Equatable,Sendable {public let message:String}
    public let business:Int
    public let lead:LeadReadItem
    public let details:Fields
    public func valid(for business:Int,id:Int)->Bool {business>0 && id>0 && self.business==business && lead.id==id && lead.valid}
}
// All generations below are local visits only. No server version or permission is inferred.
public struct LeadReadControl:Equatable,Sendable {public let context:InboxConversationFilesContext;public let visit:Int}
public struct LeadReadInput:Equatable,Sendable {public let context:InboxConversationFilesContext;public let generation:Int}
public struct LeadReadTicket:Equatable,Sendable {public let context:InboxConversationFilesContext;public let revision:Int;public let query:String;public let id:Int?;public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.revision==b.revision && SourceTextIdentity.same(a.query,b.query) && a.id==b.id}}
public struct QualifiedLeadReference:Equatable,Sendable {
    public let context:InboxConversationFilesContext
    public let readRevision:Int
    public let rawQuery:String
    public let detail:LeadReadDetail
    fileprivate init(context:InboxConversationFilesContext,readRevision:Int,rawQuery:String,detail:LeadReadDetail) {self.context=context;self.readRevision=readRevision;self.rawQuery=rawQuery;self.detail=detail}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.readRevision==b.readRevision && SourceTextIdentity.same(a.rawQuery,b.rawQuery) && a.detail==b.detail}
}
public struct LeadReadSession:Sendable {
    public private(set) var context:InboxConversationFilesContext?
    public private(set) var presented=false
    public private(set) var query=""
    public private(set) var submitted:String?
    public private(set) var items:[LeadReadItem]=[]
    public private(set) var total=0
    public private(set) var loaded=false
    public private(set) var loading=false
    public private(set) var failure:ReadFailure?
    public private(set) var selectedID:Int?
    public private(set) var detail:LeadReadDetail?
    public private(set) var choice:QualifiedLeadReference?
    private var visit=0,revision=0,inputGeneration=0
    private var pending:LeadReadTicket?
    public init() {}
    public var control:LeadReadControl? {context.map {LeadReadControl(context:$0,visit:visit)}}
    public var input:LeadReadInput? {guard presented,!loading,selectedID==nil,let context else {return nil};return LeadReadInput(context:context,generation:inputGeneration)}
    public var partial:Bool {loaded && total>items.count}
    public var showsEmpty:Bool {loaded && !loading && failure==nil && items.isEmpty && !partial}
    public var canUse:Bool {presented && !loading && failure==nil && detail != nil && detail?.valid(for:context?.business ?? 0,id:selectedID ?? 0)==true}
    private mutating func invalidate() {visit += 1;revision += 1;pending=nil;items=[];total=0;loaded=false;loading=false;failure=nil;selectedID=nil;detail=nil;choice=nil;submitted=nil}
    public mutating func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard context != next else {return};hide();context=next;query=""}
    public mutating func show() {guard context != nil else {return};if !presented {invalidate();inputGeneration += 1;presented=true}}
    public mutating func hide() {invalidate();inputGeneration += 1;presented=false}
    public mutating func update(_ value:String,input:LeadReadInput?) {guard let input,self.input==input,!SourceTextIdentity.same(value,query) else {return};invalidate();query=value}
    public mutating func clear(expected:LeadReadControl?) {guard let expected,control==expected,presented,!loading,selectedID==nil else {return};invalidate();inputGeneration += 1;query=""}
    public mutating func beginList(expected:LeadReadControl?)->LeadReadTicket? {
        guard let expected,control==expected,presented,!loading,selectedID==nil,let context else {return nil};invalidate();inputGeneration += 1;loading=true;submitted=SourceTextTrim.pythonStrip(query)
        let ticket=LeadReadTicket(context:context,revision:revision,query:submitted!,id:nil);pending=ticket;return ticket
    }
    @discardableResult public mutating func accept(_ page:LeadReadPage,ticket:LeadReadTicket)->Bool {
        guard pending==ticket,presented,context==ticket.context,ticket.id==nil else {return false};guard page.valid(for:ticket.context.business) else {fail(.invalidPayload,ticket:ticket);return false}
        pending=nil;items=page.items;total=page.summary.total;loading=false;loaded=true;failure=nil;visit += 1;return true
    }
    public mutating func beginProfile(id:Int,expected:LeadReadControl?)->LeadReadTicket? {
        guard let expected,control==expected,presented,!loading,loaded,let context,items.contains(where:{$0.id==id}),(selectedID==nil || selectedID==id) else {return nil}
        revision += 1;visit += 1;inputGeneration += 1;detail=nil;choice=nil;selectedID=id;loading=true;failure=nil
        let ticket=LeadReadTicket(context:context,revision:revision,query:SourceTextTrim.pythonStrip(query),id:id);pending=ticket;return ticket
    }
    @discardableResult public mutating func accept(_ profile:LeadReadDetail,ticket:LeadReadTicket)->Bool {
        guard pending==ticket,presented,context==ticket.context,let id=ticket.id,selectedID==id else {return false};guard profile.valid(for:ticket.context.business,id:id) else {fail(.invalidPayload,ticket:ticket);return false}
        pending=nil;detail=profile;loading=false;failure=nil;visit += 1;return true
    }
    public mutating func fail(_ error:ReadFailure,ticket:LeadReadTicket) {guard pending==ticket,presented,context==ticket.context else {return};pending=nil;loading=false;failure=error;detail=nil;choice=nil;visit += 1;if ticket.id==nil {items=[];total=0;loaded=false}}
    public mutating func cancel(ticket:LeadReadTicket) {guard pending==ticket else {return};pending=nil;loading=false;detail=nil;choice=nil;failure=nil;visit += 1;if ticket.id==nil {items=[];total=0;loaded=false}}
    public mutating func backProfile(expected:LeadReadControl?) {guard let expected,control==expected,presented,selectedID != nil else {return};revision += 1;visit += 1;inputGeneration += 1;pending=nil;loading=false;failure=nil;selectedID=nil;detail=nil;choice=nil}
    public mutating func use(expected:LeadReadControl?) {guard let expected,control==expected,canUse,let context,let detail else {return};choice=QualifiedLeadReference(context:context,readRevision:revision,rawQuery:query,detail:detail);visit += 1}
    public mutating func clearChoice(expected:LeadReadControl?) {guard let expected,control==expected,presented,!loading else {return};choice=nil;visit += 1}
}
