import Foundation

// Wire presence/raw text only. No parsed instant, chronology or local command result.
public enum InboxObservedText:Equatable,Sendable {
    case missing,null,value(String)
    public var raw:String? {if case .value(let raw)=self {return raw};return nil}
    public static func ==(a:Self,b:Self)->Bool {
        switch(a,b) {case(.missing,.missing),(.null,.null):return true;case(.value(let x),.value(let y)):return SourceTextIdentity.same(x,y);default:return false}
    }
    static func decode(_ row:[String:Any],key:String)->Self? {
        guard let value=row[key] else {return .missing};if value is NSNull {return .null};guard let raw=value as? String else {return nil};return .value(raw)
    }
}
public struct InboxMessageObservation:Equatable,Sendable {
    public let context:InboxMessageFilesContext
    public let status:InboxObservedText,sentAt:InboxObservedText,deliveredAt:InboxObservedText,readAt:InboxObservedText
    public var state:InboxMessageState {InboxMessageState(status.raw)}
    private init(context:InboxMessageFilesContext,status:InboxObservedText,sentAt:InboxObservedText,deliveredAt:InboxObservedText,readAt:InboxObservedText) {self.context=context;self.status=status;self.sentAt=sentAt;self.deliveredAt=deliveredAt;self.readAt=readAt}
    public func valid(for c:InboxMessageFilesContext)->Bool {c.valid && c==context}
    public static func decode(_ data:Data,context c:InboxMessageFilesContext)->Self? {guard let row=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else {return nil};return decode(row,context:c)}
    static func decode(_ row:[String:Any],context c:InboxMessageFilesContext)->Self? {
        guard c.valid,DirectoryReadJSON.integer(row["id"])==Int64(c.message),DirectoryReadJSON.integer(row["conversation"])==Int64(c.conversation),let status=InboxObservedText.decode(row,key:"status"),let sent=InboxObservedText.decode(row,key:"sent_at"),let delivered=InboxObservedText.decode(row,key:"delivered_at"),let read=InboxObservedText.decode(row,key:"read_at") else {return nil}
        return Self(context:c,status:status,sentAt:sent,deliveredAt:delivered,readAt:read)
    }
}
