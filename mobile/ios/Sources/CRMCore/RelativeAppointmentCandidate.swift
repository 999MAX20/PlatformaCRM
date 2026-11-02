import Foundation

// A syntactic candidate, never an ingress grant or a repository request.
// Int64 preserves the positive decimal route vocabulary without narrowing it to a
// platform's source Int. Only an independently loaded notification can corroborate.
public struct RelativeAppointmentCandidate: Equatable, Sendable {
    public let raw: String
    public let appointmentID: Int64
    private init(raw: String, appointmentID: Int64) { self.raw = raw; self.appointmentID = appointmentID }
    public static func parse(_ raw: String) -> Self? {
        let digits: Substring
        let query = "/app/calendar?appointment=", path = "/app/calendar/"
        if raw.hasPrefix(query) { digits = raw.dropFirst(query.count) }
        else if raw.hasPrefix(path) {
            let tail = raw.dropFirst(path.count)
            digits = tail.hasSuffix("/") ? tail.dropLast() : tail
        } else { return nil }
        guard !digits.isEmpty, digits.utf8.allSatisfy({ $0 >= 48 && $0 <= 57 }),
              let id = Int64(digits), id > 0, String(id) == digits else { return nil }
        return Self(raw: raw, appointmentID: id)
    }
    public func corroboratedTarget(from source: CRMNotification) -> Int? {
        guard source.valid, let target = source.appointmentTarget, Int64(target) == appointmentID else { return nil }
        return target
    }
}
