import Foundation

// Subsets of existing home/today projections. Missing sections remain unavailable.
public struct HomeSummary: Decodable, Sendable {
    public struct Appointments: Decodable, Sendable { public let today: Int }
    public struct Tasks: Decodable, Sendable { public let open: Int }
    public struct Conversations: Decodable, Sendable { public let open: Int; public let unread: Int }
    public struct Sections: Decodable, Sendable {
        public let appointments: Appointments?
        public let tasks: Tasks?
        public let conversations: Conversations?
    }
    public let business: Int
    public let sections: Sections
    public func valid(for scope: Int) -> Bool {
        scope > 0 && business == scope && (sections.appointments.map { $0.today >= 0 } ?? true) &&
        (sections.tasks.map { $0.open >= 0 } ?? true) && (sections.conversations.map { $0.open >= 0 && $0.unread >= 0 && $0.unread <= $0.open } ?? true)
    }
}
public struct TodaySummary: Decodable, Sendable {
    public struct Appointments: Decodable, Sendable {
        public let date: String
        public let total: Int
        public let items: [Appointment]
        public var partial: Bool { total > items.count }
    }
    public struct Tasks: Decodable, Sendable {
        public let date: String
        public let total: Int
        public let overdue: Int
        public let items: [WorkTask]
        public var partial: Bool { total > items.count }
    }
    public struct Sections: Decodable, Sendable { public let appointments: Appointments?; public let tasks: Tasks? }
    public struct Budget: Decodable, Sendable { public let max_items_per_section: Int }
    public let business: Int
    public let date: String
    public let limit: Int
    public let sections: Sections
    public let payload_budget: Budget
    public func valid(for scope: Int, day: String) -> Bool {
        guard scope > 0, business == scope, Day.isValid(day), date == day, (1...50).contains(limit), payload_budget.max_items_per_section == limit else { return false }
        if let a = sections.appointments {
            guard a.date == day, a.total >= a.items.count, a.items.count <= limit, Set(a.items.map(\.id)).count == a.items.count,
                  a.items.allSatisfy({ item in guard item.id > 0, let start = item.start, let end = item.end else { return false }; return end > start }) else { return false }
        }
        if let t = sections.tasks {
            guard t.date == day, t.total >= t.items.count, t.overdue >= 0, t.items.count <= limit,
                  Set(t.items.map(\.id)).count == t.items.count, t.items.allSatisfy(\.valid) else { return false }
        }
        return true
    }
}
public enum HomeDestination: String, CaseIterable, Sendable {
    case appointments, clients, inbox, tasks
    public var tabIndex: Int { switch self { case .appointments: 1; case .clients: 2; case .inbox: 3; case .tasks: 4 } }
}
