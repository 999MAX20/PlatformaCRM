import Foundation

public enum HandoffReadState: String,Sendable {case required,notRequired,unknown
    public init(_ flag: Bool?) {self=flag.map {$0 ? .required:.notRequired} ?? .unknown}
    public var copyKey: String {switch self {case .required:"handoffReadYes";case .notRequired:"handoffReadNo";case .unknown:"handoffReadUnknown"}}
}
public struct InboxConversation: Decodable, Identifiable, Sendable {
    public struct Preview: Decodable, Sendable { public let text: String? }
    public let id: Int
    public let title: String?
    public let channel: String?
    public let unread_count: Int
    public let last_message_preview: Preview?
    public let handoff_required: Bool?
    public var handoffState: HandoffReadState {HandoffReadState(handoff_required)}
    private enum CodingKeys: String,CodingKey {case id,title,channel,unread_count,last_message_preview,handoff_required}
    public init(from decoder: any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(Int.self,forKey:.id);title=try c.decodeIfPresent(String.self,forKey:.title);channel=try c.decodeIfPresent(String.self,forKey:.channel);unread_count=try c.decode(Int.self,forKey:.unread_count);last_message_preview=try c.decodeIfPresent(Preview.self,forKey:.last_message_preview)
        handoff_required=try? c.decode(Bool.self,forKey:.handoff_required)
    }
}
public struct InboxList: Decodable, Sendable {
    public struct Summary: Decodable, Sendable { public let open: Int }
    public let business: Int
    public let items: [InboxConversation]
    public let summary: Summary
    public func valid(for scope: Int) -> Bool {
        business == scope && summary.open >= items.count && Set(items.map(\.id)).count == items.count && items.allSatisfy { $0.id > 0 && $0.unread_count >= 0 }
    }
}
public enum InboxMessageState:String,Sendable {
    case received,queued,sent,failed,unknown
    public init(_ raw:String?) {self=raw.flatMap(Self.init(rawValue:)) ?? .unknown}
    public var copyKey:String {switch self {case .received:"messageStateReceived";case .queued:"messageStateQueued";case .sent:"messageStateSent";case .failed:"messageStateFailed";case .unknown:"messageStateUnknown"}}
}
public struct InboxMessage: Decodable, Identifiable, Sendable {
    public let id: Int
    public let conversation_id: Int
    public let direction: String?
    public let sender_type: String?
    public let text: String?
    public let created_at: String?
    public let sourceState:InboxMessageState
    private enum CodingKeys:String,CodingKey {case id,conversation_id,direction,sender_type,text,created_at,status}
    public init(from decoder:any Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(Int.self,forKey:.id);conversation_id=try c.decode(Int.self,forKey:.conversation_id)
        direction=try c.decodeIfPresent(String.self,forKey:.direction);sender_type=try c.decodeIfPresent(String.self,forKey:.sender_type);text=try c.decodeIfPresent(String.self,forKey:.text);created_at=try c.decodeIfPresent(String.self,forKey:.created_at)
        sourceState=InboxMessageState(try? c.decode(String.self,forKey:.status))
    }
}
public struct InboxThread: Decodable, Sendable {
    public struct Fields: Decodable, Sendable {
        public struct ClientReference: Decodable, Sendable { public let id: Int? }
        public let client: ClientReference?
        public let status: String?
    }
    public struct Budget: Decodable, Sendable { public let max_messages: Int }
    public let business: Int
    public let conversation: InboxConversation
    public let messages: [InboxMessage]
    public let payload_budget: Budget
    public let details: Fields?
    public var sourceStatus: String? { details?.status }
    public var clientReferenceID: Int? { guard let id = details?.client?.id, id > 0 else { return nil }; return id }
    public var windowCapped: Bool { messages.count == payload_budget.max_messages }
    public func valid(for scope: Int, id: Int) -> Bool {
        business == scope && conversation.id == id && conversation.unread_count >= 0 && payload_budget.max_messages > 0 && messages.count <= payload_budget.max_messages &&
        Set(messages.map(\.id)).count == messages.count && messages.allSatisfy { $0.id > 0 && $0.conversation_id == id }
    }
}
