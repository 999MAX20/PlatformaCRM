import Foundation

// Existing generic DealSerializer lens only; no mobile DTO, permission or server version.
public struct DealReadSource:Equatable,Sendable {
    public let id:Int,business:Int,client:Int
    public let lead:Int?
    public let title:String,updatedAt:String
    private init(id:Int,business:Int,client:Int,lead:Int?,title:String,updatedAt:String) {self.id=id;self.business=business;self.client=client;self.lead=lead;self.title=title;self.updatedAt=updatedAt}
    public func valid(for business:Int,id:Int)->Bool {business>0 && id>0 && self.business==business && self.id==id && client>0 && client<=Int(Int32.max) && (lead==nil || (lead!>0 && lead!<=Int(Int32.max))) && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && a.client==b.client && a.lead==b.lead && SourceTextIdentity.same(a.title,b.title) && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,business:Int,id:Int)->Self? {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max),let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],DirectoryReadJSON.integer(o["id"])==Int64(id),DirectoryReadJSON.integer(o["business"])==Int64(business),let c=DirectoryReadJSON.integer(o["client"]),c>0,c<=Int64(Int32.max),let value=o["lead"],let title=o["title"] as? String,let updated=o["updated_at"] as? String,!updated.isEmpty else {return nil}
        let lead:Int?
        if value is NSNull {lead=nil} else {guard let n=DirectoryReadJSON.integer(value),n>0,n<=Int64(Int32.max) else {return nil};lead=Int(n)}
        return Self(id:id,business:business,client:Int(c),lead:lead,title:title,updatedAt:updated)
    }
}
// Local identifier field grammar, separate from API serializer coercion.
public enum DealReferenceIdentifier {
    public static func parse(_ raw:String)->Int? {guard !raw.isEmpty,raw.unicodeScalars.allSatisfy({$0.value>=48 && $0.value<=57}),let id=Int(raw),id>0,id<=Int(Int32.max) else {return nil};return id}
}
public struct DealReferenceControl:Equatable,Sendable {public let context:InboxConversationFilesContext;public let visit:Int}
public struct DealReferenceInput:Equatable,Sendable {public let context:InboxConversationFilesContext;public let generation:Int}
public struct DealReferenceTicket:Equatable,Sendable {
    public let context:InboxConversationFilesContext,revision:Int,rawInput:String,id:Int
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.revision==b.revision && a.id==b.id && SourceTextIdentity.same(a.rawInput,b.rawInput)}
}
public struct QualifiedDealReference:Equatable,Sendable {
    public let context:InboxConversationFilesContext,readRevision:Int,rawInput:String,source:DealReadSource
    fileprivate init(context:InboxConversationFilesContext,readRevision:Int,rawInput:String,source:DealReadSource) {self.context=context;self.readRevision=readRevision;self.rawInput=rawInput;self.source=source}
    public var valid:Bool {context.valid && readRevision>0 && DealReferenceIdentifier.parse(rawInput)==source.id && source.valid(for:context.business,id:source.id)}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.readRevision==b.readRevision && SourceTextIdentity.same(a.rawInput,b.rawInput) && a.source==b.source}
}
public struct DealReferenceSession:Sendable {
    public private(set) var context:InboxConversationFilesContext?
    public private(set) var presented=false
    public private(set) var rawInput=""
    public private(set) var loading=false
    public private(set) var source:DealReadSource?
    public private(set) var failure:ReadFailure?
    public private(set) var choice:QualifiedDealReference?
    private var pending:DealReferenceTicket?
    private var revision=0,visit=0,inputGeneration=0,sourceRevision=0
    public init() {}
    public var control:DealReferenceControl? {context.map {DealReferenceControl(context:$0,visit:visit)}}
    public var input:DealReferenceInput? {guard presented,let context else {return nil};return DealReferenceInput(context:context,generation:inputGeneration)}
    public var invalidIdentifier:Bool {!rawInput.isEmpty && DealReferenceIdentifier.parse(rawInput)==nil}
    public var canRead:Bool {presented && !loading && DealReferenceIdentifier.parse(rawInput) != nil}
    public var canUse:Bool {guard presented,!loading,failure==nil,let context,let source,sourceRevision>0 else {return false};return DealReferenceIdentifier.parse(rawInput)==source.id && source.valid(for:context.business,id:source.id)}
    private mutating func invalidate() {revision += 1;visit += 1;sourceRevision=0;pending=nil;loading=false;source=nil;failure=nil;choice=nil}
    public mutating func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard next != context else {return};hide();context=next;rawInput=""}
    public mutating func show() {guard context != nil,!presented else {return};invalidate();inputGeneration += 1;presented=true}
    public mutating func hide() {invalidate();inputGeneration += 1;presented=false}
    public mutating func update(_ raw:String,input:DealReferenceInput?) {guard let input,self.input==input,!SourceTextIdentity.same(rawInput,raw) else {return};invalidate();rawInput=raw}
    public mutating func clear(expected:DealReferenceControl?) {guard let expected,control==expected,presented else {return};invalidate();inputGeneration += 1;rawInput=""}
    public mutating func begin(expected:DealReferenceControl?)->DealReferenceTicket? {guard let expected,control==expected,canRead,let context,let id=DealReferenceIdentifier.parse(rawInput) else {return nil};invalidate();loading=true;let ticket=DealReferenceTicket(context:context,revision:revision,rawInput:rawInput,id:id);pending=ticket;return ticket}
    @discardableResult public mutating func accept(_ source:DealReadSource,ticket:DealReferenceTicket)->Bool {guard pending==ticket,presented,context==ticket.context else {return false};guard source.valid(for:ticket.context.business,id:ticket.id) else {fail(.invalidPayload,ticket:ticket);return false};pending=nil;loading=false;failure=nil;self.source=source;sourceRevision=ticket.revision;visit += 1;return true}
    public mutating func fail(_ error:ReadFailure,ticket:DealReferenceTicket) {guard pending==ticket,presented,context==ticket.context else {return};pending=nil;loading=false;source=nil;sourceRevision=0;failure=error;choice=nil;visit += 1}
    public mutating func cancel(ticket:DealReferenceTicket) {guard pending==ticket else {return};pending=nil;loading=false;source=nil;sourceRevision=0;failure=nil;choice=nil;visit += 1}
    public mutating func use(expected:DealReferenceControl?) {guard let expected,control==expected,canUse,let context,let source else {return};choice=QualifiedDealReference(context:context,readRevision:sourceRevision,rawInput:rawInput,source:source);visit += 1}
    public mutating func clearChoice(expected:DealReferenceControl?) {guard let expected,control==expected,presented,!loading else {return};choice=nil;visit += 1}
}
