import Foundation

// Navigation/read state only. No booking/payment lifecycle or offline commands.
public struct AgendaSession: Sendable {
    public private(set) var businesses: [Business] = []
    public private(set) var selection: Selection?
    public private(set) var items: [Appointment] = []
    public private(set) var detail: AppointmentDetail?
    public private(set) var detailSelection: DetailSelection?
    public private(set) var isPartial = false
    public private(set) var responseDay: String?
    public var sourceDayMismatch: Bool { responseDay != nil && responseDay != selection?.day }
    private var revision = 0
    public init() {}
    public mutating func install(_ bootstrap: Bootstrap) throws {
        guard !bootstrap.businesses.isEmpty,
              Set(bootstrap.businesses.map(\.id)).count == bootstrap.businesses.count,
              bootstrap.businesses.contains(where: { $0.id == bootstrap.active_business.id && $0.timezone == bootstrap.active_business.timezone }),
              bootstrap.businesses.allSatisfy({ $0.id > 0 && TimeZone(identifier: $0.timezone) != nil }) else { throw ReadFailure.invalidPayload }
        revision += 1; businesses = bootstrap.businesses
        selection = nil; items = []; clearDetail(); isPartial = false; responseDay = nil
    }
    @discardableResult
    public mutating func begin(businessID: Int, day: String) throws -> Selection {
        guard Day.isValid(day), let business = businesses.first(where: { $0.id == businessID }) else { throw ReadFailure.invalidContext }
        revision += 1
        let scope = Selection(business: business, day: day, revision: revision)
        selection = scope; items = []; clearDetail(); isPartial = false; responseDay = nil
        return scope
    }
    @discardableResult
    public mutating func receive(_ payload: AppointmentList, for scope: Selection) throws -> Bool {
        guard selection == scope else { return false }
        guard payload.business == scope.business.id, payload.summary.total >= payload.items.count,
              Set(payload.items.map(\.id)).count == payload.items.count, payload.items.allSatisfy({ $0.id > 0 }) else { throw ReadFailure.invalidPayload }
        // Keep raw rows and source date. Presentation quarantines uncertain intervals.
        items = payload.items; isPartial = payload.isPartial; responseDay = payload.date
        return true
    }
    public mutating func beginDetail(id: Int) throws -> DetailSelection {
        guard let scope = selection, items.contains(where: { $0.id == id }) else { throw ReadFailure.invalidContext }
        revision += 1
        let request = DetailSelection(scope: scope, id: id, revision: revision)
        detail = nil; detailSelection = request
        return request
    }
    @discardableResult
    public mutating func receive(_ payload: AppointmentDetail, for request: DetailSelection) throws -> Bool {
        guard detailSelection == request, selection == request.scope else { return false }
        let scope = request.scope, id = request.id
        guard payload.business == scope.business.id, payload.appointment.id == id,
              items.contains(where: { $0.id == id }) else { throw ReadFailure.invalidPayload }
        // Fresh same-ID read replaces raw fields, including missing or moved times.
        items = items.map { $0.id == id ? payload.appointment : $0 }
        detail = payload; return true
    }
    public mutating func clearDetail() { detail = nil; detailSelection = nil }
}
