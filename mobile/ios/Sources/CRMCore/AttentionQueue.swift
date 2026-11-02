import Foundation

public struct AttentionIdentity: Hashable, Sendable { public let key: String; public let type: String; public let entityID: Int }
public enum AttentionKind: Equatable, Sendable { case task, conversation, appointment }
public struct AttentionTarget: Equatable, Sendable { public let kind: AttentionKind; public let id: Int; public init(kind: AttentionKind, id: Int) { self.kind = kind; self.id = id } }
public struct AttentionItem: Decodable, Identifiable, Sendable {
    public struct Entity: Decodable, Sendable { public let id: Int; public var title: String?; public let href: String? }
    public let key: String
    public let type: String
    public let priority: Int
    public var entity: Entity
    public var id: AttentionIdentity { AttentionIdentity(key: key, type: type, entityID: entity.id) }
    // Explicit source type/id plus exact source template. Never parse an ID from href.
    public var readTarget: AttentionTarget? {
        guard entity.id > 0 else { return nil }
        switch (key, type, entity.href) {
        case ("complete_task", "task", "/app/tasks?task=\(entity.id)"): return AttentionTarget(kind: .task, id: entity.id)
        case ("reply_conversation", "conversation", "/app/conversations?conversation=\(entity.id)"): return AttentionTarget(kind: .conversation, id: entity.id)
        case ("confirm_appointment", "appointment", "/app/calendar?appointment=\(entity.id)"): return AttentionTarget(kind: .appointment, id: entity.id)
        default: return nil
        }
    }
}
public struct AttentionPage: Decodable, Sendable {
    public struct Budget: Decodable, Sendable { public let max_items: Int }
    public let business: Int
    public let limit: Int
    public let total: Int
    public let items: [AttentionItem]
    public let payload_budget: Budget
    // Source total counts only the already truncated returned window.
    public var windowCapped: Bool { items.count == limit }
    public func valid(for scope: Int) -> Bool {
        scope > 0 && business == scope && (1...50).contains(limit) && payload_budget.max_items == limit && total == items.count &&
        items.count <= limit && items.allSatisfy { $0.entity.id > 0 } && Set(items.map(\.id)).count == items.count
    }
}
public enum AttentionDetail: Sendable {
    case task(TaskDetails), conversation(InboxThread), appointment(AppointmentDetail)
    public var title: String? { switch self { case .task(let d): d.task.title; case .conversation(let d): d.conversation.title; case .appointment(let d): d.appointment.title } }
    public func valid(for business: Int, target: AttentionTarget) -> Bool {
        switch (self, target.kind) {
        case (.task(let d), .task): return d.valid(for: business, id: target.id)
        case (.conversation(let d), .conversation): return d.valid(for: business, id: target.id)
        case (.appointment(let d), .appointment):
            guard d.business == business, d.appointment.id == target.id, let start = d.appointment.start, let end = d.appointment.end else { return false }; return end > start
        default: return false
        }
    }
}
