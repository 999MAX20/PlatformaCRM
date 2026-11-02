import Foundation

// Existing TeamMemberManagementSerializer lens; nested MobileUserItem is display identity only.
public struct TeamMemberReadSource:Equatable,Sendable {
    public let id:Int,business:Int
    public let user:MobileUserItem
    public let isActive:Bool
    public let updatedAt:String
    private init(id:Int,business:Int,user:MobileUserItem,isActive:Bool,updatedAt:String) {self.id=id;self.business=business;self.user=user;self.isActive=isActive;self.updatedAt=updatedAt}
    private struct Fields:Decodable {let user:MobileUserItem;let is_active:Bool;let updated_at:String}
    public func valid(for business:Int,id:Int)->Bool {business>0 && id>0 && self.business==business && self.id==id && user.valid && user.id<=Int(Int32.max) && !updatedAt.isEmpty}
    public static func ==(a:Self,b:Self)->Bool {a.id==b.id && a.business==b.business && a.user==b.user && a.isActive==b.isActive && SourceTextIdentity.same(a.updatedAt,b.updatedAt)}
    public static func decode(_ data:Data,business:Int,id:Int)->Self? {
        guard business>0,business<=Int(Int32.max),id>0,id<=Int(Int32.max),let o=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],DirectoryReadJSON.integer(o["id"])==Int64(id),DirectoryReadJSON.integer(o["business"])==Int64(business),let u=o["user"] as? [String:Any],let uid=DirectoryReadJSON.integer(u["id"]),uid>0,uid<=Int64(Int32.max),let f=try? JSONDecoder().decode(Fields.self,from:data),f.user.id==Int(uid),!f.updated_at.isEmpty else {return nil}
        return Self(id:id,business:business,user:f.user,isActive:f.is_active,updatedAt:f.updated_at)
    }
}
// Local identifier field grammar, separate from API serializer coercion.
public enum MemberReferenceIdentifier {
    public static func parse(_ raw:String)->Int? {guard !raw.isEmpty,raw.unicodeScalars.allSatisfy({$0.value>=48 && $0.value<=57}),let id=Int(raw),id>0,id<=Int(Int32.max) else {return nil};return id}
}
public struct MemberReferenceControl:Equatable,Sendable {public let context:InboxConversationFilesContext;public let visit:Int}
public struct MemberReferenceInput:Equatable,Sendable {public let context:InboxConversationFilesContext;public let generation:Int}
public struct MemberReferenceTicket:Equatable,Sendable {
    public let context:InboxConversationFilesContext,revision:Int,rawInput:String,id:Int
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.revision==b.revision && a.id==b.id && SourceTextIdentity.same(a.rawInput,b.rawInput)}
}
public struct QualifiedMemberReference:Equatable,Sendable {
    public let context:InboxConversationFilesContext,readRevision:Int,rawInput:String,source:TeamMemberReadSource
    fileprivate init(context:InboxConversationFilesContext,readRevision:Int,rawInput:String,source:TeamMemberReadSource) {self.context=context;self.readRevision=readRevision;self.rawInput=rawInput;self.source=source}
    public var valid:Bool {context.valid && readRevision>0 && MemberReferenceIdentifier.parse(rawInput)==source.id && source.valid(for:context.business,id:source.id) && source.isActive}
    public static func ==(a:Self,b:Self)->Bool {a.context==b.context && a.readRevision==b.readRevision && SourceTextIdentity.same(a.rawInput,b.rawInput) && a.source==b.source}
}
public struct MemberReferenceSession:Sendable {
    public private(set) var context:InboxConversationFilesContext?
    public private(set) var presented=false
    public private(set) var rawInput=""
    public private(set) var loading=false
    public private(set) var source:TeamMemberReadSource?
    public private(set) var failure:ReadFailure?
    public private(set) var choice:QualifiedMemberReference?
    private var pending:MemberReferenceTicket?
    private var revision=0,visit=0,inputGeneration=0,sourceRevision=0
    public init() {}
    public var control:MemberReferenceControl? {context.map {MemberReferenceControl(context:$0,visit:visit)}}
    public var input:MemberReferenceInput? {guard presented,let context else {return nil};return MemberReferenceInput(context:context,generation:inputGeneration)}
    public var invalidIdentifier:Bool {!rawInput.isEmpty && MemberReferenceIdentifier.parse(rawInput)==nil}
    public var canRead:Bool {presented && !loading && MemberReferenceIdentifier.parse(rawInput) != nil}
    public var canUse:Bool {guard presented,!loading,failure==nil,let context,let source,sourceRevision>0 else {return false};return MemberReferenceIdentifier.parse(rawInput)==source.id && source.valid(for:context.business,id:source.id) && source.isActive}
    private mutating func invalidate() {revision += 1;visit += 1;sourceRevision=0;pending=nil;loading=false;source=nil;failure=nil;choice=nil}
    public mutating func bind(_ next:InboxConversationFilesContext?) {let next=next?.valid==true ? next:nil;guard next != context else {return};hide();context=next;rawInput=""}
    public mutating func show() {guard context != nil,!presented else {return};invalidate();inputGeneration += 1;presented=true}
    public mutating func hide() {invalidate();inputGeneration += 1;presented=false}
    public mutating func update(_ raw:String,input:MemberReferenceInput?) {guard let input,self.input==input,!SourceTextIdentity.same(rawInput,raw) else {return};invalidate();rawInput=raw}
    public mutating func clear(expected:MemberReferenceControl?) {guard let expected,control==expected,presented else {return};invalidate();inputGeneration += 1;rawInput=""}
    public mutating func begin(expected:MemberReferenceControl?)->MemberReferenceTicket? {guard let expected,control==expected,canRead,let context,let id=MemberReferenceIdentifier.parse(rawInput) else {return nil};invalidate();loading=true;let ticket=MemberReferenceTicket(context:context,revision:revision,rawInput:rawInput,id:id);pending=ticket;return ticket}
    @discardableResult public mutating func accept(_ source:TeamMemberReadSource,ticket:MemberReferenceTicket)->Bool {guard pending==ticket,presented,context==ticket.context else {return false};guard source.valid(for:ticket.context.business,id:ticket.id) else {fail(.invalidPayload,ticket:ticket);return false};pending=nil;loading=false;failure=nil;self.source=source;sourceRevision=ticket.revision;visit += 1;return true}
    public mutating func fail(_ error:ReadFailure,ticket:MemberReferenceTicket) {guard pending==ticket,presented,context==ticket.context else {return};pending=nil;loading=false;source=nil;sourceRevision=0;failure=error;choice=nil;visit += 1}
    public mutating func cancel(ticket:MemberReferenceTicket) {guard pending==ticket else {return};pending=nil;loading=false;source=nil;sourceRevision=0;failure=nil;choice=nil;visit += 1}
    public mutating func use(expected:MemberReferenceControl?) {guard let expected,control==expected,canUse,let context,let source else {return};choice=QualifiedMemberReference(context:context,readRevision:sourceRevision,rawInput:rawInput,source:source);visit += 1}
    public mutating func clearChoice(expected:MemberReferenceControl?) {guard let expected,control==expected,presented,!loading else {return};choice=nil;visit += 1}
}
